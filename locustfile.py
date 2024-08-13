from locust import HttpUser, task, between, tag
from energyid import JSONClient
import yaml


with open("credentials.yaml") as f:
    credentials = yaml.safe_load(f)


class User(HttpUser):
    wait_time = between(1, 2.5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eid_client = JSONClient(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
        )
        self.eid_client._session = self.client

    @task
    def hello_world(self):
        self.client.get("")

    def on_start(self):
        self.eid_client.authenticate(
            username=credentials["username"],
            # username='pen1@energieid.be',
            # password='pen-test-1')
            password=credentials["password"],
        )

    @task
    def get_meter_catalog(self):
        self.eid_client.get_meter_catalog()

    @task
    def get_member(self):
        self.eid_client.get_member()

    @task
    def get_member_groups(self):
        self.eid_client.get_member_groups()

    @task
    def get_member_records(self):
        self.eid_client.get_member_records()

    @task
    @tag("meters")
    def get_meters(self):
        records = self.eid_client.get_member_records()
        for record in records:
            meters = record.get_meters()
        return meters
