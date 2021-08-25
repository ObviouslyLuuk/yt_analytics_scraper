import pygal
import csv
import matplotlib.pyplot as plt

from util.custom_values import CHANNEL_ID, DATA_DIR
PATH = DATA_DIR + f"Hourly_{CHANNEL_ID}.csv"

# Read csv
with open(PATH, "r") as f:
    reader = csv.DictReader(f)
    data = []
    keys = reader.fieldnames
    for row in reader:
        data.append(row)

# Parse data into plottable lists
x_labels = [ f'{row["date"]} {row["day"]} {row["start"]}' for row in data]
older_videos = []
newest_video = []
for row in data:
    try:
        views = int(row['views']) - int(row[keys[5]])
        new_views = int(row[keys[5]])
    except:
        views = 0
        new_views = 0
    older_videos.append(views)
    newest_video.append(new_views)


def pygal_plot() -> None:
    """
    Save a plot as svg.
    """
    bar_chart = pygal.StackedBar(width=2200, height=1000, tooltip_border_radius=5)
    bar_chart.title = 'Channel Views'
    bar_chart.x_labels = x_labels

    bar_chart.add('', older_videos)
    bar_chart.add('', newest_video)

    bar_chart.render_to_file(DATA_DIR+"channel.svg")


def mpl_simple() -> None:
    """
    Show a matplotlib plot.
    """
    video_ids = list(data[-1].keys())[4:]
    fig, axs = plt.subplots(len(video_ids), 1)
    x_labels = range(len(data))
    for i, id in enumerate(video_ids):
        video_data = []
        for row in data:
            try:
                views = int(row[id])
            except:
                views = 0
            video_data.append(views)

        axs[i].bar(x_labels, video_data)
    plt.show()


def mpl_interactive() -> None:
    """
    Show a matplotlib plot with hover annotations.

    Notes
    -----
    credit: https://stackoverflow.com/questions/50560525/how-to-annotate-the-values-of-x-and-y-while-hovering-mouse-over-the-bar-graph/50560826#50560826
    Incredibly slow
    """
    fig=plt.figure()
    ax=plt.subplot()

    bars = plt.bar(x_labels, older_videos)

    annot = ax.annotate("", xy=(0,0), xytext=(-20,20),textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="black", ec="b", lw=2),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_annot(bar, i):
        date = x_labels[i]
        x = bar.get_x()+bar.get_width()/2.
        y = bar.get_y()+bar.get_height()
        annot.xy = (x,y)
        text = f"{date}\n{y}"
        annot.set_text(text)
        annot.get_bbox_patch().set_alpha(0.4)


    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == ax:
            for i, bar in enumerate(bars):
                cont, ind = bar.contains(event)
                if cont:
                    update_annot(bar, i)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                    return
        if vis:
            annot.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)

    plt.show()


if __name__ == "__main__":
    pygal_plot()
    mpl_simple()