import os
import random
import supervisely as sly
from collections import defaultdict
import cv2

from aug_utils import validate_input_meta, aug_project_meta, aug_img_ann
from supervisely.app.v1.app_service import AppService

my_app = AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])

project = None
total_images_count = None
image_ids = []
project_meta: sly.ProjectMeta = None
new_project_meta = None
CNT_GRID_COLUMNS = 3

image_grid_options = {
    "opacity": 0.5,
    "fillRectangle": False,
    "enableZoom": False,
    "syncViews": False
}

def _count_train_val_split(train_percent, total_images_count):
    train_images_count = max(1, min(total_images_count - 1, int(total_images_count * train_percent / 100)))
    val_images_count = total_images_count - train_images_count
    split_table = [
        {"name": "total images", "count": total_images_count},
        {"name": "train images", "count": train_images_count},
        {"name": "val images", "count": val_images_count}
    ]
    return split_table

@my_app.callback("stop")
@sly.timeit
def stop(api: sly.Api, task_id, context, state, app_logger):
    remote_path = "/temp/{}/".format(task_id)
    api.file.remove(TEAM_ID, remote_path)
    api.task.set_field(task_id, "data.finished", True)

@my_app.callback("count_train_val_split")
@sly.timeit
def count_split(api: sly.Api, task_id, context, state, app_logger):
    split_table = _count_train_val_split(state["trainPercent"], total_images_count)
    api.task.set_fields(task_id, [{"field": "data.splitTable", "payload": split_table}])


@my_app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_fields(task_id, [{"field": "data.previewProgress", "payload": 0}])

    image_id = random.choice(image_ids)
    image_info = api.image.get_info_by_id(image_id)
    img_url = image_info.path_original

    img = api.image.download_np(image_info.id)
    ann_json = api.annotation.download(image_id).annotation
    ann = sly.Annotation.from_json(ann_json, project_meta)

    res_meta = aug_project_meta(project_meta, state)
    combined_meta = project_meta.merge(res_meta)

    imgs_anns = aug_img_ann(img, ann, res_meta, state)
    imgs_anns = [(img, ann)] + imgs_anns

    # TODO: for debug
    #ann.draw(img)
    #cv2.imwrite("/workdir/ann.png", img)

    grid_data = {}
    grid_layout = [[] for i in range(CNT_GRID_COLUMNS)]

    @sly.timeit
    def _upload_augs():
        if len(imgs_anns) == 0:
            api.task.set_fields(task_id, [{"field": "data.showEmptyMessage", "payload": True}])
            return

        upload_src_paths = []
        upload_dst_paths = []
        for idx, (cur_img, cur_ann) in enumerate(imgs_anns):
            img_name = "{:03d}.png".format(idx)
            remote_path = "/temp/{}/{}".format(task_id, img_name)
            if api.file.exists(TEAM_ID, remote_path):
                api.file.remove(TEAM_ID, remote_path)
            local_path = "{}/{}".format(my_app.data_dir, img_name)
            sly.image.write(local_path, cur_img)
            #api.file.upload(TEAM_ID, local_path, remote_path)
            upload_src_paths.append(local_path)
            upload_dst_paths.append(remote_path)

        api.file.remove(TEAM_ID, "/temp/{}/".format(task_id))
        def _progress_callback(monitor):
            if hasattr(monitor, 'last_percent') is False:
                monitor.last_percent = 0
            cur_percent = int(monitor.bytes_read * 100.0 / monitor.len)
            if cur_percent - monitor.last_percent > 15 or cur_percent == 100:
                api.task.set_fields(task_id, [{"field": "data.previewProgress", "payload": cur_percent}])
                monitor.last_percent = cur_percent

        upload_results = api.file.upload_bulk(TEAM_ID, upload_src_paths, upload_dst_paths, _progress_callback)
        #clean local data
        for local_path in upload_src_paths:
            sly.fs.silent_remove(local_path)
        return upload_results

    upload_results = _upload_augs()

    for idx, info in enumerate(upload_results):
        grid_data[info.name] = {"url": info.path_original,
                                "figures": [label.to_json() for label in imgs_anns[idx][1].labels]}
        grid_layout[idx % CNT_GRID_COLUMNS].append(info.name)

    if len(grid_data) > 0:
        content = {
            "projectMeta": combined_meta.to_json(),
            "annotations": grid_data,
            "layout": grid_layout
        }
        api.task.set_fields(task_id, [{"field": "data.preview.content", "payload": content}])

def sample_images(api, datasets, state):
    split_table = _count_train_val_split(state["trainPercent"], total_images_count)
    train_images_count = split_table[1]["count"]

    all_images = []
    for dataset in datasets:
        images = api.image.get_list(dataset.id)
        all_images.extend(images)
    cnt_images = len(all_images)

    shuffled_images = all_images.copy()
    random.shuffle(shuffled_images)

    train_images = shuffled_images[:train_images_count]
    val_images = shuffled_images[train_images_count:]

    ds_images_train = defaultdict(list)
    for image_info in train_images:
        ds_images_train[image_info.dataset_id].append(image_info)

    ds_images_val = defaultdict(list)
    for image_info in val_images:
        ds_images_val[image_info.dataset_id].append(image_info)

    return ds_images_train, ds_images_val, cnt_images

@my_app.callback("create_trainset")
@sly.timeit
def create_trainset(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "data.started", True)

    project = api.project.get_info_by_id(PROJECT_ID)
    meta = sly.ProjectMeta.from_json(api.project.get_meta(project.id))
    res_meta = aug_project_meta(meta, state)

    result_project_name = state["resultProjectName"]
    if not result_project_name:
        result_project_name = _get_res_project_name(api, project)
    new_project = api.project.create(WORKSPACE_ID, result_project_name,
                                     description="for SmartTool",
                                     change_name_if_conflict=True)
    api.project.update_meta(new_project.id, res_meta.to_json())

    datasets = api.dataset.get_list(PROJECT_ID)
    ds_images_train, ds_images_val, sample_count = sample_images(api, datasets, state)

    train_tag = res_meta.get_tag_meta("train")
    val_tag = res_meta.get_tag_meta("val")
    splitted_images = []

    for dataset_id, images in ds_images_train.items():
        splitted_images.append((dataset_id, images, train_tag))
    for dataset_id, images in ds_images_val.items():
        splitted_images.append((dataset_id, images, val_tag))

    progress = sly.Progress("Augmentations", total_images_count)

    _created_datasets = {}
    current_progress = 0
    for (dataset_id, images, tag)  in splitted_images:
        dataset = api.dataset.get_info_by_id(dataset_id)

    # for dataset in datasets:
        if dataset.name not in _created_datasets:
            new_dataset = api.dataset.create(new_project.id, dataset.name)
            _created_datasets[dataset.name] = new_dataset
        new_dataset = _created_datasets[dataset.name]

        #images = api.image.get_list(dataset.id)

        used_names = []
        for batch in sly.batched(images):
            image_ids = [image_info.id for image_info in batch]
            image_names = [image_info.name for image_info in batch]
            images_np = api.image.download_nps(dataset.id, image_ids)
            ann_infos = api.annotation.download_batch(dataset.id, image_ids)
            new_annotations = []
            new_images = []
            new_images_names = []
            for image_np, image_name, ann_info in zip(images_np, image_names, ann_infos):
                used_names.append(image_name)
                ann = sly.Annotation.from_json(ann_info.annotation, meta)
                ann = ann.clone(img_tags=sly.TagCollection([tag]))

                imgs_anns = aug_img_ann(image_np, ann, res_meta, state)
                if len(imgs_anns) == 0:
                    continue

                for (aug_img, aug_ann) in imgs_anns:
                    new_images.append(aug_img)
                    name = sly._utils.generate_free_name(used_names, image_name, with_ext=True)
                    new_images_names.append(name)
                    new_annotations.append(aug_ann)
                    used_names.append(name)

            new_image_infos = api.image.upload_nps(new_dataset.id, new_images_names, new_images)
            image_ids = [img_info.id for img_info in new_image_infos]
            api.annotation.upload_anns(image_ids, new_annotations)
            progress.iters_done_report(len(batch))
            current_progress += len(batch)
            api.task.set_field(task_id, "data.progress", int(current_progress * 100 / total_images_count))

    # to get correct "reference_image_url"
    res_project = api.project.get_info_by_id(new_project.id)
    fields = [
        {"field": "data.resultProject", "payload": res_project.name},
        {"field": "data.resultProjectId", "payload": res_project.id},
        {"field": "data.resultProjectPreviewUrl",
         "payload": api.image.preview_url(res_project.reference_image_url, 100, 100)},
        {"field": "data.finished", "payload": True}
    ]
    api.task.set_fields(task_id, fields)
    api.task.set_output_project(task_id, res_project.id, res_project.name)

    my_app.stop()


def _get_res_project_name(api, project):
    res_project_name = "{} (train SmartTool)".format(project.name)
    res_project_name = api.project.get_free_name(WORKSPACE_ID, res_project_name)
    return res_project_name


def main():
    api = sly.Api.from_env()
    global project, total_images_count, image_ids, project_meta, new_project_meta

    project = api.project.get_info_by_id(PROJECT_ID)
    project_meta = sly.ProjectMeta.from_json(api.project.get_meta(project.id))
    validate_input_meta(project_meta)

    res_project_name = _get_res_project_name(api, project)

    train_percent = 95
    total_images_count = api.project.get_images_count(project.id)
    split_table = _count_train_val_split(train_percent, total_images_count)

    for dataset in api.dataset.get_list(project.id):
        image_infos = api.image.get_list(dataset.id)
        image_ids.extend([info.id for info in image_infos])

    my_app.logger.info("Image ids are initialized", extra={"count": len(image_ids)})

    data = {
        "projectId": project.id,
        "projectName": project.name,
        "projectPreviewUrl": api.image.preview_url(project.reference_image_url, 100, 100),
        "progress": 0,
        "started": False,
        "totalImagesCount": total_images_count,
        "splitTable": split_table,
        "preview": {"content": {}, "options": image_grid_options},
        "previewProgress": 0,
        "showEmptyMessage": False,
        "finished": False
    }

    state = {
        "trainPercent": train_percent,
        "filterThresh": 30,
        "paddingRange": [5, 15],
        "minPointsCount": 0,
        "inputWidth": 256,
        "inputHeight": 256,
        "className": "obj",
        "posClassName": "pos",
        "negClassName": "neg",
        "flipHorizontal": True,
        "flipVertical": False,
        "imageDuplicate": 1,
        "resultProjectName": res_project_name
    }

    initial_events = [
        {
            "state": state,
            "context": None,
            "command": "preview",
        }
    ]

    # Run application service
    my_app.run(data=data, state=state, initial_events=initial_events)

#@TODO: empty message never shows
#@TODO: bulk upload to files to optimize preview
#@TODO: customize icon and add positive/negative points
#@TODO: create modal html
if __name__ == "__main__":
    sly.main_wrapper("main", main)
