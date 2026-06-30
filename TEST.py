API_KEY = "你的FUGLE_KEY"

def clean_key(key):
    return str(key).strip().replace("\n", "").replace("\r", "")

api_key = clean_key(API_KEY)

headers = {
    "X-API-KEY": api_key
}
