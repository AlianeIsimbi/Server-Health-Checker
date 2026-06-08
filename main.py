import json
import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor

# FEATURE 8: Track failed services
failed_services = []

def track_failure(url, result):
    if not result.get("healthy", False):
        failed_services.append(url)


# FEATURE 1 & 9: Load servers (ENV first, fallback to file)
def load_servers():
    env_servers = os.getenv("SERVERS")

    if env_servers:
        servers = [s.strip() for s in env_servers.split(",") if s.strip()]
        print(f"Loaded {len(servers)} servers from ENV")
        return servers

    with open("config.json", "r") as file:
        data = json.load(file)

    servers = data["servers"]

    print(f"Loaded {len(servers)} servers from file")
    return servers


# FEATURE 2 + 3 + 4: Check server + timing + health rules
def check_server(url):
    start_time = time.time()

    try:
        response = requests.get(url, timeout=5)
        response_time = (time.time() - start_time) * 1000

        healthy = 200 <= response.status_code < 300

        result = {
            "url": url,
            "status_code": response.status_code,
            "response_time": round(response_time, 2),
            "healthy": healthy,
            "error": None,
            "json_ok": False
        }

        # FEATURE 5: JSON validation
        try:
            data = response.json()
            if data.get("status") == "ok":
                result["json_ok"] = True
        except:
            pass

        return result

    except requests.exceptions.RequestException:
        return {
            "url": url,
            "status_code": None,
            "response_time": None,
            "healthy": False,
            "error": "Request failed",
            "json_ok": False
        }


# FEATURE 6: Slow service detection
def add_slow_flag(result):
    if result.get("response_time") is not None:
        result["slow"] = result["response_time"] > 500
    else:
        result["slow"] = False
    return result


# FEATURE 7: Format output
def format_result(result):

    if result.get("error"):
        return f"{result['url']} — TIMEOUT"

    status = "OK" if result["healthy"] else "DOWN"

    output = (
        f"{result['url']} — "
        f"{status} ({result['status_code']}) — "
        f"{result['response_time']}ms"
    )

    if result.get("slow"):
        output += " [slow]"

    if result.get("json_ok"):
        output += " [json ok]"

    return output


# FEATURE 11: Parallel execution
def check_all_servers():
    servers = load_servers()

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(check_server, servers))

    # post-processing features
    for r in results:
        add_slow_flag(r)
        track_failure(r["url"], r)

    return results


# Main execution
if __name__ == "__main__":

    results = check_all_servers()

    for r in results:
        print(format_result(r))

    print("\nFailed services:")

    for f in failed_services:
        print(f)