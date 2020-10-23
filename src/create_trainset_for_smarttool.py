import os
import random
import string
import supervisely_lib as sly

# https://git.deepsystems.io/deepsystems/supervisely_py/-/merge_requests/1/diffs

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])


@my_app.callback("apply_to_random_image")
@sly.timeit
def apply_to_random_image(api: sly.Api, task_id, context, state, app_logger):
    pass

@my_app.callback("create_trainset")
def do(api: sly.Api, task_id, context, state, app_logger):
    print("123")
    pass

def main():
    api = sly.Api.from_env()
    project = api.project.get_info_by_id(PROJECT_ID)

    data = {
        "projectId": project.id,
        "projectName": project.name,
        "projectPreviewUrl": api.image.preview_url(project.reference_image_url, 100, 100),
        "progress": 0,
        "started": False
    }

    state = {
        "filterPercent": 5,
        "paddingRange": [5, 10]
    }

    initial_events = [
        {
            "state": None,
            "context": None,
            "command": "apply_to_random_image",
        }
    ]

    # Run application service
    my_app.run(data=data, state=state, initial_events=initial_events)


if __name__ == "__main__":
    sly.main_wrapper("main", main)