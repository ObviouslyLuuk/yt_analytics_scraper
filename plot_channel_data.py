import pygal
import csv

PATH = "D:\\Users\\Luuk\\Documents\\Programming\\stuff\\yt_realtime_data\\channel_mainChart.csv"

with open(PATH, "r") as f:
    reader = csv.DictReader(f)
    data = []
    keys = reader.fieldnames
    for row in reader:
        data.append(row)

bar_chart = pygal.StackedBar(width=2200, height=1000, tooltip_border_radius=5)
bar_chart.title = 'Views'
bar_chart.x_labels = [ f'{row["date"]} {row["day"]} {row["start"]}' for row in data]

older_videos = []
newest_video = []
for row in data:
    try:
        views = int(row['views']) - int(row[keys[-3]])
        new_views = int(row[keys[-3]])
    except:
        views = 0
        new_views = 0
    older_videos.append(views)
    newest_video.append(new_views)
bar_chart.add('', older_videos)
bar_chart.add('', newest_video)

bar_chart.render_to_file("channel.svg")