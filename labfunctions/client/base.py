import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Union

import httpx
import jwt

from labfunctions import defaults, errors, log, types
from labfunctions.client.labstate import LabState
from labfunctions.client.utils import get_credentials_disk, store_credentials_disk
from labfunctions.events import EventManager
from labfunctions.hashes import generate_random
from labfunctions.utils import mkdir_p, open_yaml, write_yaml


def get_http_client(**kwargs) -> httpx.Client:

    return httpx.Client(**kwargs)


class AuthFlow(httpx.Auth):
    requires_request_body = True
    requires_response_body = True

    def __init__(self, access_token, refresh_token, refresh_url, homedir=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_url = refresh_url
        self._homedir = homedir

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        response = yield request

        # is_valid = validate_credentials_local(self.access_token)
        if response.status_code == 401:
            # If the server issues a 401 response, then issue a request to
            # refresh tokens, and resend the request.
            refresh_response = yield self.build_refresh_request()
            self.update_tokens(refresh_response)

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request

    def build_refresh_request(self):
        # Return an `httpx.Request` for refreshing tokens.
        rtkn = {"refresh_token": self.refresh_token}
        req = httpx.Request("POST", self.refresh_url, json=rtkn)
        req.headers["Authorization"] = f"Bearer {self.access_token}"
        return req

    def update_tokens(self, response):
        # Update the `.access_token` and `.refresh_token` tokens
        # based on a refresh response.
        data = response.json()
        tkn = data.get("access_token")
        if not tkn:
            raise errors.AuthValidationFailed()
        self.access_token = tkn
        self.refresh_token = data.get("refresh_token")
        if self._homedir:
            store_credentials_disk(self.creds, self._homedir)

    @property
    def creds(self):
        return types.TokenCreds(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
        )


class BaseClient:
    """
    A Generic client for API Server communication.


    By default, each client is associated to a specific project,
    this could be decoupled in the future because some actions
    like **startproject** are independent of the project.

    **Some conventions:**

    If a method calls to an API's endpoint, it should use the name
    of the endpoint at first. For instance:

        GET /workflows/<projectid>/<wfid>
    The method name for that endpoint could be: `workflows_get_one()`


    :param url_service: base url of the WORKFLOWS_SERVICE
    :param projectid: projectid realted to ProjectsModel
    :param creds: TokenCreds type, it includes access_token and refresh_token
    :param store_creds: Optional, if true the credentials will be stored on disk
    :param project: Optional[Project] type
    :param version: version api, not implemented yet
    :param http_init_func: Callable, a function which initializes
    a HTTPX client.
    """

    def __init__(
        self,
        url_service: str,
        creds: Optional[types.TokenCreds] = None,
        lab_state: Optional[LabState] = None,
        version=defaults.API_VERSION,
        http_init_func=get_http_client,
        timeout=defaults.CLIENT_TIMEOUT,
        base_path: Optional[str] = None,
    ):
        self._addr = url_service
        self._creds = creds
        self._auth: Optional[AuthFlow] = None
        self.logger = log.client_logger
        self.state = lab_state
        self._version = version
        self._timeout = timeout
        self._http_creator = http_init_func
        self._http: httpx.Client = self._http_init()
        self.base_path = base_path
        self._home = Path.home() / defaults.CLIENT_HOME_DIR

    @property
    def working_area(self) -> Path:
        """Working area is used to store related project data as private keys
        temp build generation files and so on"""

        return self._home / self.projectid

    @property
    def homedir(self) -> Path:
        return self._home

    def create_homedir(self) -> Path:
        if not self._home.is_dir():
            mkdir_p(self._home)
            self._home.chmod(0o700)
        return self._home

    def info(self) -> types.client.ClientInfo:
        workflows = []
        filepath = None
        if self.state and self.state.workflows:
            workflows = list(self.state.workflows.keys())
            filepath = self.state.filepath
        pid = self.projectid

        return types.client.ClientInfo(
            projectid=pid,
            project_name=self.project_name,
            workflows_service=self._addr,
            homedir=str(self.homedir),
            labfile=filepath,
            workflows=workflows,
            user=self.user,
            base_path=self.base_path,
        )

    @property
    def http(self) -> httpx.Client:
        return self._http

    @property
    def projectid(self) -> Union[str, None]:
        if self.state:
            return self.state.projectid
        return None

    @property
    def project_name(self) -> Union[str, None]:
        if self.state:
            return self.state.project_name
        return None

    def _auth_init(self):
        self._auth = AuthFlow(
            self._creds.access_token,
            self._creds.refresh_token,
            f"{self._addr}/{self._version}/{defaults.REFRESH_TOKEN_PATH}",
            homedir=self.homedir,
        )

    def _http_init(self) -> httpx.Client:
        """When token is updated the client MUST BE updated too."""
        # _headers = {"Authorization": f"Bearer {self.creds.access_token}"}

        if self._creds:
            self._auth_init()
        return self._http_creator(
            base_url=f"{self._addr}/{self._version}",
            timeout=self._timeout,
            auth=self._auth,
        )

    @property
    def user(self) -> Union[types.client.UserInfo, None]:
        if self._creds:
            decoded = jwt.decode(
                self._creds.access_token, options={"verify_signature": False}
            )

            return types.client.UserInfo(
                username=decoded["usr"], scopes=decoded["scopes"]
            )
        return None

    @property
    def creds(self) -> Union[types.TokenCreds, None]:
        if not self._auth:
            return None

        return self._auth.creds

    @creds.setter
    def creds(self, creds: types.TokenCreds):
        """
        If credentials are set, the http client should be
        re-initialized
        """
        self._creds = creds
        self._http = self._http_init()
        # if self._creds:
        #    store_credentials_disk(self.creds, self.homedir)

    def load_creds(self) -> types.TokenCreds:
        """first it will try to load creds from homedir
        if fails, then it will look at environement variables
        if it founds the credentials then store locally
        """
        creds = get_credentials_disk(self.homedir)
        if creds:
            self.creds = creds
        else:
            at = os.getenv(defaults.AGENT_TOKEN_ENV)
            rt = os.getenv(defaults.AGENT_REFRESH_ENV)
            if at and rt:
                creds = types.TokenCreds(access_token=at, refresh_token=rt)
                self.creds = creds
                store_credentials_disk(self.creds, self.homedir)
            else:
                raise errors.CredentialsNotFound(self.homedir, defaults.AGENT_TOKEN_ENV)

        return creds

    def login(self, u: str, p: str, store_creds=True):
        rsp = httpx.post(
            f"{self._addr}/{self._version}/auth/login",
            json=dict(username=u, password=p),
            timeout=self._timeout,
        )
        if rsp.status_code == 200:
            self.creds = types.TokenCreds(**rsp.json())
            if store_creds:
                store_credentials_disk(self.creds, self.homedir)

        else:
            raise errors.client.LoginError(self._addr, u)

    def verify(self):
        rsp = self._http.get(f"/auth/verify")
        if rsp.status_code == 200:
            self.creds = self._auth.creds
            return True
        else:
            self._creds = None
            self._auth = None
            return False

    def write(self, output=defaults.LABFILE_NAME):
        self.state.write(output)

    def close(self):
        self._http.close()

    def events_listen(
        self, execid, last=None, timeout=None
    ) -> Generator[types.events.EventSSE, None, None]:
        timeout = timeout or self._timeout
        # uri = f"/events/{self.projectid}/{execid}/_listen"
        uri = f"{self._addr}/{self._version}/events/{self.projectid}/{execid}/_listen"
        if last:
            uri = f"{uri}?last={last}"

        headers = {"Authorization": f"Bearer {self.creds.access_token}"}

        with httpx.stream("GET", uri, timeout=timeout, headers=headers) as r:
            buffer_ = ""
            for line in r.iter_lines():
                buffer_ += line
                if buffer_.endswith("\n\n"):
                    evt = EventManager.from_sse2event(buffer_)
                    # print(evt.dict())
                    if evt.data == "exit":
                        return
                    yield evt
                    buffer_ = ""

    def events_publish(self, execid, data, event=None):
        final = data
        if isinstance(data, dict):
            final = json.dumps(data)
        if final:
            evt = types.events.EventSSE(data=final, event=event)
            self._http.post(
                f"/events/{self.projectid}/{execid}/_publish", json=evt.dict()
            )
        else:
            self.logger.warning(f"execid: {execid} empty message")
