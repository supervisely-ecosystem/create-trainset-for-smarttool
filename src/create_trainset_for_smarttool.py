import os
import random
import string
import supervisely_lib as sly

from aug_utils import validate_input_meta, aug_project_meta

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

image_grid_options = {
    "rows": 3,
    "columns": 3,
    "opacity": 0.8,
    "fillRectangle": False
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
    image = api.image.get_info_by_id(image_id)

    img_url = image.full_storage_url

    ann_json = api.annotation.download(image_id).annotation
    ann = sly.Annotation.from_json(ann_json, project_meta)

    obj_class_name = state["className"]
    pos_class_name = state["posClassName"]
    neg_class_name = state["negClassName"]
    res_meta, obj_class, pos_class, neg_class, train_tag, val_tag = \
        aug_project_meta(project_meta, obj_class_name, pos_class_name, neg_class_name)

    content = {
        "projectMeta": project_meta.to_json(),
        "annotations": [
            {"url": image.full_storage_url, "figures": [label.to_json() for label in ann.labels]},
            {"url": image.full_storage_url, "figures": []},
            {"url": image.full_storage_url, "figures": []},
            {"url": image.full_storage_url, "figures": []},
            {"url": image.full_storage_url, "figures": []},
        ],
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
        "preview": {"content": {}, "options": image_grid_options}
    }

    state = {
        "trainPercent": train_percent,
        "filterPercent": 5,
        "paddingRange": [5, 10],
        "minPointsCount": 0,
        "inputWidth": 256,
        "inputHeight": 256,
        "className": "obj",
        "posClassName": "pos",
        "negClassName": "neg"
    }

    initial_events = [
        {
            "state": None,
            "context": None,
            "command": "preview",
        }
    ]

    # Run application service
    my_app.run(data=data, state=state, initial_events=initial_events)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
