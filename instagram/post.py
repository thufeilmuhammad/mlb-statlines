import os
import json
import requests
import datetime

APPROVED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'approved_post.json')
GRAPH_API = "https://graph.facebook.com/v21.0"


def upload_image(image_path):
    """Upload image to catbox.moe and return a public URL."""
    with open(image_path, 'rb') as f:
        r = requests.post(
            'https://catbox.moe/user/api.php',
            data={'reqtype': 'fileupload'},
            files={'fileToUpload': ('image.png', f, 'image/png')},
            timeout=60,
        )
    r.raise_for_status()
    url = r.text.strip()
    if not url.startswith('http'):
        raise RuntimeError(f"Image upload failed: {url}")
    return url


def create_media_container(ig_user_id, access_token, image_url, caption):
    r = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media",
        params={
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if 'error' in data:
        raise RuntimeError(f"Container error: {data['error']}")
    return data['id']


def publish_media(ig_user_id, access_token, creation_id):
    r = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media_publish",
        params={
            'creation_id': creation_id,
            'access_token': access_token,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if 'error' in data:
        raise RuntimeError(f"Publish error: {data['error']}")
    return data


def post_to_instagram():
    if not os.path.exists(APPROVED_FILE):
        print("No approved_post.json found — nothing to post.")
        return False

    with open(APPROVED_FILE) as f:
        post = json.load(f)

    if post.get('posted'):
        print("Already posted today — skipping.")
        return False

    ig_user_id   = os.environ['INSTAGRAM_ACCOUNT_ID']
    access_token = os.environ['INSTAGRAM_ACCESS_TOKEN']
    image_path   = post['image_path']
    caption      = post['caption']

    # Resolve relative path from repo root
    if not os.path.isabs(image_path):
        repo_root  = os.path.join(os.path.dirname(__file__), '..')
        image_path = os.path.normpath(os.path.join(repo_root, image_path))

    print(f"Uploading image: {image_path}")
    image_url = upload_image(image_path)
    print(f"Hosted at: {image_url}")

    print("Creating media container...")
    creation_id = create_media_container(ig_user_id, access_token, image_url, caption)

    print(f"Publishing container {creation_id}...")
    result    = publish_media(ig_user_id, access_token, creation_id)
    ig_post_id = result.get('id', '')
    print(f"Posted! Instagram post ID: {ig_post_id}")

    post['posted']     = True
    post['posted_at']  = datetime.datetime.now().isoformat()
    post['ig_post_id'] = ig_post_id
    with open(APPROVED_FILE, 'w') as f:
        json.dump(post, f, indent=2)

    return True


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    post_to_instagram()
