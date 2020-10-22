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


def do(project_meta, img, ann):
    pass


def main():
    api = sly.Api.from_env()

    data = {
        "randomString": "hello!"
    }

    state = {
        "prefix": "abc_"
    }

    initial_events = [
        {
            "state": None,
            "context": None,
            "command": "preprocessing",
        }
    ]

    # Run application service
    my_app.run(data=data, state=state, initial_events=initial_events)


if __name__ == "__main__":
    sly.main_wrapper("main", main)