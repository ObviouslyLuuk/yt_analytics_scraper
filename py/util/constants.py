from enum import Enum

from .custom_values import CHANNEL_ID

# CONSTANTS -------------------------------------------------------------------

class ScrapeMode(Enum):
    channel = 0
    video = 1

ANALYTICS_URL       = "https://studio.youtube.com/{mode}/{id}/analytics/tab-overview/period-default"
VIDEOS_URL          = "https://studio.youtube.com/channel/{channel_id}/videos/{upload_or_live}"
VIDEO_URL           = "https://www.youtube.com/watch?v={video_id}"
DAYS_OF_THE_WEEK    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# -----------------------------------------------------------------------------

METRICS = { # These are the metrics that show granular data
    "views"         : "VIEWS",
    "impressions"   : "VIDEO_THUMBNAIL_IMPRESSIONS",
    "watchtime"     : "WATCH_TIME",
    "likes"         : "RATINGS_LIKES",
    "dislikes"      : "RATINGS_DISLIKES",
}
class TimePeriod(Enum):
    first_24h = "since_publish%2Ctime_period_unit_nth_days%2C1"
    since_published = "since_publish"

# These traffic sources show impressions data
TRAFFIC_SOURCES_IMP = { # All of these have _main at the end
    "MAIN_METRIC_SERIES_NAME"       : "Total",
	"YT_PLAYLIST_PAGE_main"         : "Playlist page",
	"PLAYLIST_main"                 : "Playlists",
	"YT_RELATED_main"               : "Suggested videos",
	"YT_SEARCH_main"                : "YouTube search",
	"YT_CHANNEL_main"               : "Channel pages",
	"SUBSCRIBER_main"               : "Browse features",
}
# TRAFFIC_SOURCES is the complete dictionary
TRAFFIC_SOURCES = {
	"END_SCREEN_main"               : "End screens",
	"NOTIFICATION_main"             : "Notifications",
	"EXT_URL_main"                  : "External",
	"YT_OTHER_PAGE_main"            : "Other YouTube features",
	"UNKNOWN_MOBILE_OR_DIRECT_main" : "Direct or unknown",
    "SHORTS_main"                   : "Shorts feed",
    "ADVERTISING_main"              : "Advertising",
    "ANNOTATION_main"               : "Cards and annotations",
    "HASHTAGS_main"                 : "Hashtag pages",
}
TRAFFIC_SOURCES.update(TRAFFIC_SOURCES_IMP)
# Inverted dictionary
TRAFFIC_SOURCES_INV = {v: k for k, v in TRAFFIC_SOURCES.items()}

class Dimensions(Enum):
    total = "VIDEO"
    traffic_source = "TRAFFIC_SOURCE_TYPE"

# The URL for the Advanced Analytics display
ADV_URL             = "https://studio.youtube.com/channel/{channel_id}/analytics/tab-overview/period-default/explore?entity_type=VIDEO&entity_id={video_id}&time_period={time_period}&explore_type=TABLE_AND_CHART&metric={metric}&granularity=DAY&t_metrics=RATINGS_DISLIKES&t_metrics=RATINGS_LIKES&t_metrics=VIEWS&t_metrics=WATCH_TIME&t_metrics=AVERAGE_WATCH_TIME&t_metrics=VIDEO_THUMBNAIL_IMPRESSIONS&t_metrics=VIDEO_THUMBNAIL_IMPRESSIONS_VTR&v_metrics=VIEWS&v_metrics=WATCH_TIME&v_metrics=SUBSCRIBERS_NET_CHANGE&v_metrics=TOTAL_ESTIMATED_EARNINGS&v_metrics=VIDEO_THUMBNAIL_IMPRESSIONS&v_metrics=VIDEO_THUMBNAIL_IMPRESSIONS_VTR&dimension={dimension}&o_column=VIEWS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC".format(
    channel_id      = CHANNEL_ID,
    video_id        = "{video_id}",
    time_period     = "{time_period}",
    metric          = "{metric}",
    dimension       = "{dimension}",
)

# OTHER -----------------------------------------------------------------------

THUMBNAIL_URL       = "http://img.youtube.com/vi/{}/maxresdefault.jpg"

# # These traffic sources show impressions data
# TRAFFIC_SOURCES_IMP = { # All of these have _main at the end
#     "Total"                     : "MAIN_METRIC_SERIES_NAME",
# 	"Playlist page"             : "YT_PLAYLIST_PAGE_main",
# 	"Playlists"                 : "PLAYLIST_main",
# 	"Suggested videos"          : "YT_RELATED_main",
# 	"YouTube search"            : "YT_SEARCH_main",
# 	"Channel pages"             : "YT_CHANNEL_main",
# 	"Browse features"           : "SUBSCRIBER_main",
# }
# # TRAFFIC_SOURCES is the complete dictionary
# TRAFFIC_SOURCES = {
# 	"End screens"               : "END_SCREEN_main",
# 	"Notifications"             : "NOTIFICATION_main",
# 	"External"                  : "EXT_URL_main",
# 	"Other YouTube features"    : "YT_OTHER_PAGE_main",
# 	"Direct or unknown"         : "UNKNOWN_MOBILE_OR_DIRECT_main",
#     "Shorts feed"               : "SHORTS_main",    
# }

# class TrafficSourcesImp(Enum):
#     total = "MAIN_METRIC_SERIES_NAME"
#     playlist_page = "YT_PLAYLIST_PAGE_main"
#     playlist = "PLAYLIST_main"
#     suggested = "YT_RELATED_main"
#     search = "YT_SEARCH_main"
#     channel = "YT_CHANNEL_main"
#     browse = "SUBSCRIBER_main"
# class TrafficSources(TrafficSourcesImp):
#     end_screen = "END_SCREEN_main"
#     notification = "NOTIFICATION_main"
#     external = "EXT_URL_main"
#     other_yt = "YT_OTHER_PAGE_main"
#     direct_or_unknown = "UNKNOWN_MOBILE_OR_DIRECT_main"
#     shorts = "SHORTS_main"