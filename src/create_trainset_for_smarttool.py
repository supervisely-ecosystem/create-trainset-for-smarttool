import os
import random
import string
import json
import supervisely_lib as sly

from aug_utils import validate_input_meta, aug_project_meta, aug_img_ann

# https://git.deepsystems.io/deepsystems/supervisely_py/-/merge_requests/1/diffs

my_app = sly.AppService()

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


@my_app.callback("create_trainset")
def do(api: sly.Api, task_id, context, state, app_logger):
    print("123")
    pass


def _count_train_val_split(train_percent, total_images_count):
    train_images_count = max(1, min(total_images_count - 1, int(total_images_count * train_percent / 100)))
    val_images_count = total_images_count - train_images_count
    split_table = [
        {"name": "total images", "count": total_images_count},
        {"name": "train images", "count": train_images_count},
        {"name": "val images", "count": val_images_count}
    ]
    return split_table


@my_app.callback("count_train_val_split")
@sly.timeit
def count_split(api: sly.Api, task_id, context, state, app_logger):
    split_table = _count_train_val_split(state["trainPercent"], total_images_count)
    api.task.set_fields(task_id, [{"field": "data.splitTable", "payload": split_table}])


@my_app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    image_id = random.choice(image_ids)
    image_info = api.image.get_info_by_id(image_id)
    img_url = image_info.full_storage_url

    img = api.image.download_np(image_info.id)
    ann_json = api.annotation.download(image_id).annotation
    ann = sly.Annotation.from_json(ann_json, project_meta)

    res_meta = aug_project_meta(project_meta, state)
    combined_meta = project_meta.merge(res_meta)

    imgs_anns = aug_img_ann(img, ann, res_meta, state)
    imgs_anns = [(img, ann)] + imgs_anns

    grid_data = {}
    grid_layout = [[] for i in range(CNT_GRID_COLUMNS)]

    @sly.timeit
    def _upload_augs():
        for idx, (img, ann) in enumerate(imgs_anns):
            img_name = "{:03d}.png".format(idx)
            remote_path = "/temp/{}/{}".format(task_id, img_name)
            if api.file.exists(TEAM_ID, remote_path):
                api.file.remove(TEAM_ID, remote_path)
            local_path = "{}/{}".format(my_app.data_dir, img_name)
            sly.image.write(local_path, img)
            api.file.upload(TEAM_ID, local_path, remote_path)
            sly.fs.silent_remove(local_path)
            info = api.file.get_info_by_path(TEAM_ID, remote_path)
            grid_data[img_name] = {"url": info.full_storage_url, "figures": [label.to_json() for label in ann.labels]}
            grid_layout[idx % CNT_GRID_COLUMNS].append(img_name)
            api.task.set_fields(task_id, [{"field": "data.previewProgress", "payload": int((idx + 1) * 100.0 / len(imgs_anns))}])

    _upload_augs()

    content = {
        "projectMeta": combined_meta.to_json(),
        "annotations": grid_data,
        "layout": grid_layout
    }
    api.task.set_fields(task_id, [{"field": "data.preview.content", "payload": content}])


def main():
    api = sly.Api.from_env()
    global project, total_images_count, image_ids, project_meta, new_project_meta

    project = api.project.get_info_by_id(PROJECT_ID)
    project_meta = sly.ProjectMeta.from_json(api.project.get_meta(project.id))
    validate_input_meta(project_meta)

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
        "previewProgress": 0
    }

    state = {
        "trainPercent": train_percent,
        "filterThresh": 135, #@TODO: for debug - return to 100
        "paddingRange": [5, 10],
        "minPointsCount": 0,
        "inputWidth": 256,
        "inputHeight": 256,
        "className": "obj",
        "posClassName": "pos",
        "negClassName": "neg",
        "flipHorizontal": True,
        "flipVertical": False
    }

    initial_events = [
        {
            "state": state,
            "context": None,
            "command": "preview",
        }
    ]

    # Run application service
    # filter percent - reimplement - filter by min side
    # filter - заменить слайдер на input number
    # TODO: add original image to grid
    my_app.run(data=data, state=state, initial_events=initial_events)

#@TODO: found image without labels, try again
if __name__ == "__main__":
    sly.main_wrapper("main", main)
