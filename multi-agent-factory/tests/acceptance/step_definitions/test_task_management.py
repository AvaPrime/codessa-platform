from pytest_bdd import scenarios, given, when, then
from tests.acceptance.fixtures import api_client, admin_user

scenarios('../features/task_management.feature')

@given('I am authenticated as an admin user')
def authenticated_admin(admin_user, api_client):
    api_client.authenticate(admin_user)

@when('I submit a documentation task with valid parameters')
def submit_doc_task(api_client):
    response = api_client.post('/tasks', json={
        'role': 'doc_writer',
        'payload': {'doc_type': 'api', 'content': 'Create API docs'}
    })
    api_client.last_response = response

@then('the task should be accepted')
def task_accepted(api_client):
    assert api_client.last_response.status_code == 201