import os
import base64
import json
import config
from datetime import datetime
import urllib.request


def is_alert(log_dict, threshold):
    total_slot_ms = int(log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics'].get('totalSlotMs', '0'))
    total_processed_bytes = int(log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics'].get('totalProcessedBytes', '0'))
    total_billed_bytes = int(log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics'].get('totalBilledBytes', '0'))
    if total_slot_ms > threshold['total_slot_ms']:
        return True
    if total_processed_bytes > threshold['total_processed_bytes']:
        return True
    if total_billed_bytes > threshold['total_processed_bytes']:
        return True
    return False


def parse_alert_job_info(log_dict, threshold):
    user_email = log_dict['protoPayload']['authenticationInfo']['principalEmail']
    total_slot_ms = int(log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics'].get('totalSlotMs', '0'))
    total_processed_bytes = int(log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics'].get('totalProcessedBytes', '0'))
    total_billed_bytes = int(log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics'].get('totalBilledBytes', '0'))
    creation_time = log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics']['createTime']
    end_time = log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobStatistics']['endTime']
    job_id = log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobName']['jobId']
    project_id = log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobName']['projectId']
    location = log_dict['protoPayload']['serviceData']['jobCompletedEvent']['job']['jobName']['location']
    job_result_url = f'https://console.cloud.google.com/bigquery?project={project_id}&j=bq:{location}:{job_id}&page=queryresults'
    total_processed_bytes_gb = total_processed_bytes / 1000 / 1000 / 1000
    total_billed_bytes_gb = total_processed_bytes / 1000 / 1000 / 1000
    creation_time_dt = datetime.strptime(creation_time, '%Y-%m-%dT%H:%M:%S.%f%z')
    end_time_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%f%z')
    duration_dt = end_time_dt - creation_time_dt
    duration_minutes = duration_dt.total_seconds()
    alert_job_info_text = f"JobId: <{job_result_url}|{project_id}:{location}.{job_id}>" + "\n" + \
                         f"TotalSlotMs: {total_slot_ms} (AlertThreshold: {threshold['total_slot_ms']})" + "\n" + \
                         f"TotalProcessedBytes: {total_processed_bytes_gb:.02f}GB (AlertThreshold: {threshold['total_processed_bytes']/1000/1000/1000/1000}TB)" + "\n" + \
                         f"TotalBilledBytes: {total_billed_bytes_gb:.02f}GB (AlertThreshold: {threshold['total_billed_bytes']/1000/1000/1000/1000}TB)" + "\n" + \
                         f"DurationTime: {duration_minutes}sec" + "\n" + \
                         f"UserEmail: {user_email}"
    return alert_job_info_text


def post_slack(alert_text):
    headers = {
        'Content-Type': 'application/json',
    }
    message_text = config.SLACK_ALERT_MESSAGE_TEXT
    message_attachments_fields = [
        {
            'title': 'Alert JobInfo',
            'value': alert_text,
            'short': False
        },
        {
            'title': 'Hint',
            'value': '<https://cloud.google.com/bigquery/docs/best-practices-performance-overview | BigQueryベストプラクティス - クエリパフォーマンスの最適化の概要>',
            'short': False
        },
    ]
    payload = {
        'icon_emoji': config.SLACK_ICON_EMOJI,
        'username': config.SLACK_USERNAME,
        'text': message_text,
        'channel': config.SLACK_CHANNEL,
        'attachments': [
            {
                'fallbac': 'fallback',
                'color': 'danger',
                'fields': message_attachments_fields
            },
        ],
    }
    req = urllib.request.Request(config.SLACK_WEBHOOK_URL, json.dumps(payload).encode(), headers)
    with urllib.request.urlopen(req) as res:
        body = res.read().decode('utf-8')
        print(f'Slack incomming-webhook response:{body}')


def run(event, context):
    print(event)
    alert_threshold = {
        'total_slot_ms': config.SLOT_ALERT_THRESHOLD,
        'total_processed_bytes': config.PROCESSED_BYTE_ALERT_THRESHOLD,
        'total_billed_bytes': config.BILLED_BYTE_ALERT_THRESHOLD,
    }
    message = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    if is_alert(message, alert_threshold):
        alert_job_info_text = parse_alert_job_info(message, alert_threshold)
        post_slack(alert_job_info_text)
