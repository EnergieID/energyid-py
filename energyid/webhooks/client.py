from typing import Dict, Optional
import aiohttp

import requests


class WebhookClient:
    def __init__(self, webhook_url: str, session: Optional[requests.Session] = None):
        self.webhook_url = webhook_url
        self.session = session if session is not None else requests.Session()

    def get(self) -> Dict:
        r = self.session.get(url=self.webhook_url)
        r.raise_for_status()
        return r.json()
    
    def post(self, data: Dict):
        r = self.session.post(url=self.webhook_url, json=data)
        r.raise_for_status()
        return
    

class WebhookClientAsync(WebhookClient):
    def __init__(self, webhook_url: str, session: Optional[aiohttp.ClientSession] = None):
        session = session if session is not None else aiohttp.ClientSession()
        super(WebhookClientAsync, self).__init__(webhook_url=webhook_url, session=session)

    async def get(self) -> Dict:
        async with self.session.get(url=self.webhook_url) as r:
            r.raise_for_status()
            return await r.json()
        
    async def post(self, data: Dict):
        async with self.session.post(url=self.webhook_url, json=data) as r:
            r.raise_for_status()
            return