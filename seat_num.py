import requests
import json
import time
import os
from datetime import datetime

# 디스코드 Webhook 주소 (환경변수에서 불러옴)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 열람실 ID 및 필터 좌석
ROOM_IDS = [101, 102]
TARGET_SEAT_CODES = {1, 2, 3, 4, 21, 22, 23, 392, 393, 394, 395, 396, 397, 398, 405, 406, 407, 408}

# 로그인 정보 (환경변수에서 불러옴)
LOGIN_PAYLOAD = {
    "loginId": os.getenv("LIBRARY_LOGIN_ID"),
    "password": os.getenv("LIBRARY_PASSWORD"),
    "isFamilyLogin": False,
    "isMobile": False
}

LOGIN_HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://library.konkuk.ac.kr/login"
}

def get_access_token():
    response = requests.post(
        "https://library.konkuk.ac.kr/pyxis-api/api/login",
        json=LOGIN_PAYLOAD,
        headers=LOGIN_HEADERS
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return data["data"]["accessToken"]
    return None


def get_seat_data(token):
    headers = {
        "Pyxis-Auth-Token": token,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko",
        "Referer": "https://library.konkuk.ac.kr/library-services/smuf/reading-rooms/101",
        "User-Agent": "Mozilla/5.0"
    }
    all_seats = []
    for room_id in ROOM_IDS:
        url = f"https://library.konkuk.ac.kr/pyxis-api/1/api/rooms/{room_id}/seats"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            all_seats.extend(res_json.get("data", {}).get("list", []))
    return all_seats


def send_to_discord(filtered_seats):
    message_lines = [
        f"📢 **건국대 도서관 좌석 현황 (남은 시간 순)**\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    for seat in filtered_seats:
        status = "사용 중" if seat['isOccupied'] else "비어 있음"
        line = f"- 좌석 {seat['code']} → {status} | 남은 시간: {seat['remaining']}분 / 총: {seat['total']}분"
        message_lines.append(line)

    payload = {
        "content": "\n".join(message_lines)
    }

    response = requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers={
        "Content-Type": "application/json"
    })
    if response.status_code == 204:
        print("✅ 디스코드 전송 완료:", datetime.now())
    else:
        print("❌ 디스코드 전송 실패:", response.status_code)


def run_monitor():
    while True:
        print("⏳ 데이터 수집 중...")

        token = get_access_token()
        if not token:
            print("❌ 로그인 실패, 1분 후 재시도")
            time.sleep(60)
            continue

        seat_list = get_seat_data(token)
        filtered = []

        for seat in seat_list:
            code_str = seat.get("code")
            if not code_str or not code_str.isdigit():
                continue
            code = int(code_str)
            if code in TARGET_SEAT_CODES:
                filtered.append({
                    "code": code,
                    "isOccupied": seat.get("isOccupied", False),
                    "remaining": seat.get("remainingTime", 0),
                    "total": seat.get("chargeTime", 0)
                })

        # 남은 시간 오름차순 정렬
        filtered.sort(key=lambda s: s["remaining"])
        send_to_discord(filtered)

        print("🕐 다음 전송까지 대기 (5분)")
        time.sleep(300)


# 시작
if __name__ == "__main__":
    run_monitor()