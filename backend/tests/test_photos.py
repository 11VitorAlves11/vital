"""Progress photos.

The test that matters most is the one proving the metadata is gone. A photo of
someone's body carrying the GPS fix of the room it was taken in is the worst
thing this feature could ship, and "we call a strip function" is not evidence —
reading the stored bytes back is.
"""

import io
import uuid
from typing import Any

import piexif
import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import get_settings
from tests.conftest import UserFactory

# Lisbon, roughly. Written into the upload so its absence afterwards is a fact.
GPS = {
    piexif.GPSIFD.GPSLatitudeRef: b"N",
    piexif.GPSIFD.GPSLatitude: ((38, 1), (43, 1), (0, 1)),
    piexif.GPSIFD.GPSLongitudeRef: b"W",
    piexif.GPSIFD.GPSLongitude: ((9, 1), (8, 1), (0, 1)),
}


def make_photo(
    size: tuple[int, int] = (600, 900), orientation: int | None = None, gps: bool = True
) -> bytes:
    """A JPEG with the metadata a phone would attach."""
    image = Image.new("RGB", size, (90, 120, 200))
    # A gradient, so a rotation is detectable in the pixels afterwards.
    for x in range(min(size[0], 40)):
        for y in range(min(size[1], 40)):
            image.putpixel((x, y), (255, 255, 255))

    exif: dict[str, Any] = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    exif["0th"][piexif.ImageIFD.Make] = b"ACME"
    exif["0th"][piexif.ImageIFD.Model] = b"Phone 12"
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = b"2026:02:14 08:30:00"
    if orientation is not None:
        exif["0th"][piexif.ImageIFD.Orientation] = orientation
    if gps:
        exif["GPS"] = GPS

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=piexif.dump(exif))
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _storage_root(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path), raising=False)


async def upload(
    client: AsyncClient, content: bytes | None = None, **fields: Any
) -> dict[str, Any]:
    data = {"taken_on": "2026-02-14", "pose": "frente", **fields}
    response = await client.post(
        "/api/photos",
        files={"file": ("progresso.jpg", content or make_photo(), "image/jpeg")},
        data=data,
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestMetadata:
    async def test_the_stored_photo_carries_no_exif_at_all(self, user_client: AsyncClient) -> None:
        photo = await upload(user_client)

        stored = (await user_client.get(f"/api/photos/{photo['id']}/file")).content

        with Image.open(io.BytesIO(stored)) as image:
            assert not image.getexif()
        # And nothing hiding outside the tags Pillow surfaces.
        assert b"ACME" not in stored
        assert b"Phone 12" not in stored
        assert b"2026:02:14 08:30:00" not in stored

    async def test_the_location_is_gone(self, user_client: AsyncClient) -> None:
        photo = await upload(user_client)

        stored = (await user_client.get(f"/api/photos/{photo['id']}/file")).content

        assert piexif.load(stored)["GPS"] == {}

    async def test_a_rotated_photo_is_stored_upright(self, user_client: AsyncClient) -> None:
        """Orientation 6 means "rotate 90° clockwise to view". Stripping the tag
        without applying it would leave every phone photo on its side."""
        photo = await upload(user_client, make_photo(size=(600, 900), orientation=6))

        # 600x900 viewed through orientation 6 is 900x600 upright.
        assert (photo["width"], photo["height"]) == (900, 600)


class TestGallery:
    async def test_lists_newest_first(self, user_client: AsyncClient) -> None:
        await upload(user_client, taken_on="2025-06-01")
        await upload(user_client, taken_on="2026-02-14")

        photos = (await user_client.get("/api/photos")).json()

        assert [photo["taken_on"] for photo in photos] == ["2026-02-14", "2025-06-01"]

    async def test_filters_by_pose(self, user_client: AsyncClient) -> None:
        await upload(user_client, pose="frente")
        await upload(user_client, pose="lado")

        photos = (await user_client.get("/api/photos?pose=lado")).json()

        assert [photo["pose"] for photo in photos] == ["lado"]

    async def test_filters_by_date_window(self, user_client: AsyncClient) -> None:
        await upload(user_client, taken_on="2025-06-01")
        await upload(user_client, taken_on="2026-02-14")

        photos = (await user_client.get("/api/photos?from=2026-01-01")).json()

        assert [photo["taken_on"] for photo in photos] == ["2026-02-14"]

    async def test_reports_the_stored_dimensions(self, user_client: AsyncClient) -> None:
        """The gallery reserves the right box before the image arrives."""
        photo = await upload(user_client, make_photo(size=(400, 600)))

        assert (photo["width"], photo["height"]) == (400, 600)

    async def test_shrinks_a_photo_past_the_cap(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "photo_max_dimension", 300, raising=False)

        photo = await upload(user_client, make_photo(size=(1200, 600)))

        assert (photo["width"], photo["height"]) == (300, 150)

    async def test_deleting_removes_the_file_too(self, user_client: AsyncClient) -> None:
        photo = await upload(user_client)

        assert (await user_client.delete(f"/api/photos/{photo['id']}")).status_code == 204

        assert (await user_client.get(f"/api/photos/{photo['id']}/file")).status_code == 404
        assert (await user_client.get("/api/photos")).json() == []


class TestUploadRules:
    async def test_rejects_a_file_that_is_not_an_image(self, user_client: AsyncClient) -> None:
        response = await user_client.post(
            "/api/photos",
            files={"file": ("notes.jpg", b"not an image at all", "image/jpeg")},
            data={"taken_on": "2026-02-14", "pose": "frente"},
        )
        assert response.status_code == 415

    async def test_rejects_a_file_over_the_limit(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "upload_max_bytes", 512, raising=False)

        response = await user_client.post(
            "/api/photos",
            files={"file": ("big.jpg", make_photo(size=(900, 900)), "image/jpeg")},
            data={"taken_on": "2026-02-14", "pose": "frente"},
        )
        assert response.status_code == 413

    async def test_refuses_a_decompression_bomb(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A small file that decodes to more pixels than the cap allows."""
        monkeypatch.setattr(get_settings(), "photo_max_pixels", 10_000, raising=False)

        response = await user_client.post(
            "/api/photos",
            files={"file": ("bomb.jpg", make_photo(size=(900, 900)), "image/jpeg")},
            data={"taken_on": "2026-02-14", "pose": "frente"},
        )
        assert response.status_code == 415


class TestIsolation:
    async def test_one_account_cannot_list_anothers_photos(self, make_user: UserFactory) -> None:
        ana, _ = await make_user("F")
        bruno, _ = await make_user("M")
        await upload(ana)

        assert (await bruno.get("/api/photos")).json() == []

    async def test_one_account_cannot_open_anothers_photo(self, make_user: UserFactory) -> None:
        ana, _ = await make_user("F")
        bruno, _ = await make_user("M")
        photo = await upload(ana)

        assert (await bruno.get(f"/api/photos/{photo['id']}/file")).status_code == 404

    async def test_one_account_cannot_delete_anothers_photo(self, make_user: UserFactory) -> None:
        ana, _ = await make_user("F")
        bruno, _ = await make_user("M")
        photo = await upload(ana)

        assert (await bruno.delete(f"/api/photos/{photo['id']}")).status_code == 404
        assert len((await ana.get("/api/photos")).json()) == 1

    async def test_every_endpoint_needs_a_session(self, client: AsyncClient) -> None:
        photo_id = uuid.uuid4()
        assert (await client.get("/api/photos")).status_code == 401
        assert (await client.get(f"/api/photos/{photo_id}/file")).status_code == 401
        assert (await client.delete(f"/api/photos/{photo_id}")).status_code == 401

    async def test_the_file_is_never_publicly_cacheable(self, user_client: AsyncClient) -> None:
        photo = await upload(user_client)

        response = await user_client.get(f"/api/photos/{photo['id']}/file")

        assert "private" in response.headers["cache-control"]
