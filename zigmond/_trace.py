#
#    Copyright 2019 Verto Lab LLC
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
from copy import deepcopy

import requests
from datetime import datetime as dt

from .consts import ENDPOINT, APP_KEY_ENV_VAR_NAME


class AppKeyError(Exception):
    pass


def trace_req_resp(app_key: str = None):
    """
    Wrap your Lambda entry point with this decorator, supplying your App key. Zigmond will then automatically
    trace requests and responses of your skill for you to analyze in the dashboard.

    :param app_key: Your Zigmond App Key as supplied by Verto Lab
    :return:
    """
    try:
        app_key_val = app_key if isinstance(app_key, str) else os.environ[APP_KEY_ENV_VAR_NAME]
    except KeyError:
        raise AppKeyError(f'You should either supply your app_key explicitly, or set the {APP_KEY_ENV_VAR_NAME} '
                          f'environment variable')

    def internal_trace(original_f):
        def trace_and_call_f(*args, **kwargs):
            should_report = False
            event, f_resp = None, None
            try:
                event, context = deepcopy(args[0]), args[1]
                request = event.get('request')
                if request:
                    should_report = True
            except Exception as e:
                pass
            try:
                f_resp = original_f(*args, **kwargs)
                return f_resp
            finally:
                if should_report:
                    report = dict(request=event)
                    if f_resp:
                        report['response'] = f_resp
                        report['response_ts'] = dt.now().isoformat(timespec='seconds') + 'Z'
                    try:
                        requests.post(ENDPOINT, json=report, headers={'X-Zigmond-App-Key': app_key_val}, timeout=3)
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                        pass
        return trace_and_call_f

    if app_key is None or isinstance(app_key, str):
        return internal_trace
    else:
        return internal_trace(app_key)
