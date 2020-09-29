import os
import random
import string
import supervisely_lib as sly

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
    image_id = 313996

    project = api.project.get_info_by_id(PROJECT_ID)
    image_info = api.image.get_info_by_id(image_id)
    

    x = 10
    return


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
        }#,
        # {
        #     "state": None,
        #     "context": None,
        #     "command": "stop",
        # }
    ]

    # Run application service
    my_app.run(data=data, state=state, initial_events=initial_events)
    my_app.wait_all()


if __name__ == "__main__":
    sly.main_wrapper("main", main)