import os
import random
import string
import supervisely_lib as sly

# https://git.deepsystems.io/deepsystems/supervisely_py/-/merge_requests/1/diffs

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])

project = None
total_images_count = None


@my_app.callback("create_trainset")
def do(api: sly.Api, task_id, context, state, app_logger):
    print("123")
    pass


def _count_train_val_split(train_percent, total_images_count):
    train_images_count = max(1, min(total_images_count - 1, int(total_images_count * train_percent / 100)))
    val_images_count = total_images_count - train_images_count
    split_table = [
        {"name": "total", "count": total_images_count},
        {"name": "train", "count": train_images_count},
        {"name": "val", "count": val_images_count}
    ]
    return split_table


@my_app.callback("count_train_val_split")
@sly.timeit
def do(api: sly.Api, task_id, context, state, app_logger):
    split_table = _count_train_val_split(state["trainPercent"], total_images_count)
    api.task.set_fields(task_id, [{"field": "data.splitTable", "payload": split_table}])


def main():
    api = sly.Api.from_env()
    global project, total_images_count

    project = api.project.get_info_by_id(PROJECT_ID)
    train_percent = 95
    total_images_count = api.project.get_images_count(project.id)
    split_table = _count_train_val_split(train_percent, total_images_count)


    data = {
        "projectId": project.id,
        "projectName": project.name,
        "projectPreviewUrl": api.image.preview_url(project.reference_image_url, 100, 100),
        "progress": 0,
        "started": False,
        "totalImagesCount": total_images_count,
        "splitTable": split_table
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
        # {
        #     "state": None,
        #     "context": None,
        #     "command": "apply_to_random_image",
        # }
    ]

    # Run application service
    my_app.run(data=data, state=state, initial_events=initial_events)


if __name__ == "__main__":
    sly.main_wrapper("main", main)