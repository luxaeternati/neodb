"""
Qobuz
"""

import logging
import time

import httpx
import requests
from django.conf import settings

from catalog.common import *
from catalog.models import *
from catalog.music.utils import upc_to_gtin_13
from common.models.lang import detect_language

from .douban import *

_logger = logging.getLogger(__name__)


@SiteManager.register
class Qobuz(AbstractSite):
    SITE_NAME = SiteName.Qobuz
    ID_TYPE = IdType.Qobuz
    URL_PATTERNS = [
        r"^\w+://play\.qobuz\.com/album/([a-zA-Z0-9]+).*",
        ]
    WIKI_PROPERTY_ID = "?"
    DEFAULT_MODEL = Album

    @classmethod
    def id_to_url(cls, id_value):
        return f"https://play.qobuz.com/album/{id_value}"


    def scrape(self):
        user_agent_string = settings.NEODB_USER_AGENT
        user_auth_token = settings.QOBUZ_AUTH_TOKEN
        app_id = settings.QOBUZ_APP_ID
        headers = {
            "User-Agent": user_agent_string,
        }
        api_url = f"https://www.qobuz.com/api.json/0.2/album/get?app_id={app_id}&user_auth_token={user_auth_token}&album_id={self.id_value}"
        res_data = BasicDownloader(api_url, headers=headers).download().json()

        title = res_data["title"]

        artist = []
        for artist_dict in res_data["artists"]:
            artist.append(artist_dict["name"])

        genre = res_data.get("genres_list", [])

        duration = 0
        track_list = []
        for track in res_data["tracks"]["items"]:
            duration += track["duration"] * 1000
            track_list_name = None
            if track["media_number"]:
               track_list_name = "CD" + str(track["media_number"]) + " - "
            if track["work"]:
                track_list.append(
                    track_list_name
                    + str(track["track_number"]) + ". "
                    + track["work"] + " - "
                    + track["title"]
                    )
            else:
                track_list.append(
                    track_list_name
                    + str(track["track_number"])
                    + ". " + track["title"]
                )
        track_list = "\n".join(track_list)

        release_date = res_data["release_date_original"]

        company = res_data["label"]["name"]

        cover_image_url = res_data["image"]["small"]

        lang = detect_language(title)

        pd = ResourceContent(
            metadata={
                "title": title,
                "localized_title": [{"lang": lang, "text": title}],
                "artist": artist,
                "genre": genre,
                "track_list": track_list,
                "release_date": release_date,
                "duration": duration,
                "company": company,
                "brief": None,
                "cover_image_url": cover_image_url
            }
        )

        gtin = None
        if res_data["upc"]:
            gtin = upc_to_gtin_13(res_data["upc"])
        if gtin:
            pd.lookup_ids[IdType.GTIN] = gtin

        return pd
