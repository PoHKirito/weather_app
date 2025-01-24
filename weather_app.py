from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Constants for JMA API URLs
AREA_LIST_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

def get_regions():
    """Fetch area list and parse regions for selection."""
    try:
        response = requests.get(AREA_LIST_URL)
        response.raise_for_status()
        area_data = response.json()

        regions = []
        seen = set()
        for center_key, center_value in area_data.get("centers", {}).items():
            for child_code in center_value.get("children", []):
                if child_code in seen:
                    continue
                seen.add(child_code)
                office_info = area_data.get("offices", {}).get(child_code, {})
                regions.append({
                    "name": office_info.get("name", "Unknown"),
                    "code": child_code
                })
        return regions
    except requests.RequestException as e:
        print(f"Error fetching region data: {e}")
        return []

def parse_forecast_data(forecast_data):
    """Parse detailed forecast data for frontend consumption."""
    parsed_data = []
    if not isinstance(forecast_data, dict):
        print("Invalid forecast data format.")
        return parsed_data

    for time_series in forecast_data.get("timeSeries", []):
        time_defines = time_series.get("timeDefines", [])
        for area in time_series.get("areas", []):
            area_name = area.get("area", {}).get("name", "Unknown")
            weather = area.get("weather", [])
            temps = area.get("temps", [])
            pops = area.get("pops", [])
            winds = area.get("winds", [])
            waves = area.get("waves", [])

            for i, date in enumerate(time_defines):
                parsed_data.append({
                    "Date": date,
                    "Area": area_name,
                    "Weather": weather[i] if i < len(weather) else "情報なし",
                    "Temperature": temps[i] if i < len(temps) else "--",
                    "Precipitation": pops[i] if i < len(pops) else "--",
                    "Wind": winds[i] if i < len(winds) else "--",
                    "Wave": waves[i] if i < len(waves) else "--"
                })
    return parsed_data

@app.route('/')
def index():
    """Render the index page with area selection."""
    regions = get_regions()
    return render_template('index.html', regions=regions)

@app.route('/forecast', methods=['POST'])
def forecast():
    """Provide detailed forecast data as JSON."""
    area_code = request.json.get('area_code')
    if not area_code:
        return jsonify({"error": "地域コードが指定されていません。"}), 400

    try:
        forecast_url = FORECAST_URL_TEMPLATE.format(area_code=area_code)
        response = requests.get(forecast_url)
        response.raise_for_status()
        forecast_data = response.json()

        if not isinstance(forecast_data, list) or len(forecast_data) == 0:
            return jsonify({"error": "天気予報データが見つかりません。"}), 404

        parsed_data = parse_forecast_data(forecast_data[0])  # 只取第一项，避免无关数据
        return jsonify(parsed_data)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"天気予報の取得に失敗しました: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"不明なエラーが発生しました: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
