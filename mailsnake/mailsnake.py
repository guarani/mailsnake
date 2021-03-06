import requests
from requests.compat import basestring

try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except ImportError:
            raise ImportError('A json library is required to use ' + \
                             'this python library. Lol, yay for ' + \
                             'being verbose. ;)')

from .exceptions import *


class MailSnake(object):
    def __init__(self,
                 apikey='',
                 extra_params=None,
                 api='api',
                 api_section=''):
        """
            Cache API key and address.
        """
        self.apikey = apikey
        self.api = api

        self.default_params = {'apikey': apikey}
        extra_params = extra_params or {}
        if api == 'mandrill':
            self.default_params = {'key':apikey}
            if api_section != '':
                self.api_section = api_section
            else:
                # Mandrill divides the api into different sections
                for x in ['users', 'messages', 'tags', 'rejects',
                          'senders', 'urls', 'templates', 'webhooks']:
                    setattr(self, x, MailSnake(apikey, extra_params,
                                              api, x))
        self.default_params.update(extra_params)

        if '-' in self.apikey:
            self.dc = self.apikey.split('-')[1]
        api_info = {
            'api':(self.dc,'.api.','mailchimp','1.3/?method='),
            'sts':(self.dc,'.sts.','mailchimp','1.0/'),
            'export':(self.dc,'.api.','mailchimp','export/1.0/'),
            'mandrill':('','','mandrillapp','api/1.0/'),
        }
        self.api_url = 'https://%s%s%s.com/%s' % api_info[api]

    def call(self, method, params=None):
        url = self.api_url
        if self.api == 'mandrill':
            url += (self.api_section + '/' + method + '.json')
        elif self.api == 'sts':
            url += (method + '.json/')
        else:
            url += method

        params = params or {}
        params.update(self.default_params)

        if self.api == 'api' or self.api == 'mandrill':
            data = json.dumps(params)
            if self.api == 'api':
                data = requests.utils.quote(data)
            headers = {'content-type':'application/json'}
        else:
            data = params
            headers = {'content-type':
                      'application/x-www-form-urlencoded'}
        
        try:
            if self.api == 'export':
                req = requests.post(url, params=data, headers=headers)
            else:
                req = requests.post(url, data=data, headers=headers)
        except requests.exceptions.RequestException as e:
            raise HTTPRequestException(e)
            
        if req.status_code != 200:
            raise HTTPRequestException(req.status_code)

        try:
            if self.api == 'export':
                rsp = [json.loads(i) for i in \
                      req.text.split('\n')[0:-1]]
            else:
                rsp = json.loads(req.text)
        except json.JSONDecodeError as e:
            raise ParseException(e.message)

        if not isinstance(rsp, (int, bool, basestring)) and \
                'error' in rsp and 'code' in rsp:
            try:
                Err = exception_for_code(rsp['code'])
            except KeyError:
                raise SystemException(rsp['error'])
            raise Err(rsp['error'])

        return rsp

    def __getattr__(self, method_name):
        def get(self, *args, **kwargs):
            params = dict((i, j) for (i, j) in enumerate(args))
            params.update(kwargs)
            # Some mandrill functions use - in the name
            return self.call(method_name.replace('_', '-'), params)

        return get.__get__(self)
