"""Load testing script for AgroMap Uzbekistan."""
import time
from locust import HttpUser, task, between

class MapUserBehavior(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session."""
        # Login if needed
        pass

    @task(3)
    def view_map(self):
        """Most common task - viewing the map."""
        self.client.get("/")
        self.client.get("/static/css/map.css")
        self.client.get("/static/js/app.js")

    @task(2)
    def get_region_data(self):
        """Get region data from API."""
        self.client.get("/api/regions")

    @task(2)
    def get_crop_data(self):
        """Get crop data from API."""
        self.client.get("/api/crops")

    @task(1)
    def get_weather_data(self):
        """Get weather data from API."""
        self.client.get("/api/weather")
