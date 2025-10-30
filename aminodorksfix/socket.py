from time import (
    time,
    sleep
)

from .constants import (
    WS_URL,
    RECONNECT_TIME
)

from threading import Thread
from sys import _getframe as getframe
from websocket import WebSocketApp
from json import loads

from .lib.util.helpers import signature
from .lib.util.objects import Event


class SocketHandler:
    __slots__ = (
        "_client",
        "_debug",
        "_active",
        "_headers",
        "_socket",
        "_socket_thread",
        "_socket_trace",
        "_reconnect_thread"
    )

    def __init__(
            self,
            client,
            socket_trace: bool = False,
            socket_enabled: bool = True,
            debug: bool = False
    ):
        self._client = client
        self._debug = debug
        self._active = False
        self._headers = None
        self._socket: WebSocketApp | None = None
        self._socket_thread = None
        self._socket_trace = socket_trace

        if socket_enabled:
            self._reconnect_thread = Thread(target=self._reconnect_handler)
            self._reconnect_thread.start()
    
    @property
    def socket(self) -> WebSocketApp:
        if not self._socket:
            raise Exception("Socket is not connected")
        return self._socket

    def _reconnect_handler(self):
        while True:
            sleep(RECONNECT_TIME)

            if self._active:
                if self._debug:
                    print("[socket][reconnect_handler] Reconnecting Socket")

                self.close()
                self.run_amino_socket()

    def handle_message(self, ws, data):
        self._client.handle_socket_message(data)
        return

    def send(self, data):
        if self._debug:
            print(f"[socket][send] Sending Data : {data}")

        if not self._socket_thread:
            self.run_amino_socket()
            sleep(5)

        self.socket.send(data)

    def run_amino_socket(self):
        try:
            if self._debug:
                print("[socket][start] Starting Socket")

            if not self._client.sid:
                return

            final = f"{self._client.device_id}|{int(time() * 1000)}"

            self._headers = {
                "NDCDEVICEID": self._client.device_id,
                "NDCAUTH": f"sid={self._client.sid}",
                "NDC-MSG-SIG": signature(final)
            }

            self._socket = WebSocketApp(
                url=f"{WS_URL}/?signbody={final.replace('|', '%7C')}",
                on_message=self.handle_message,
                header=self._headers
            )

            self._active = True
            self._socket_thread = Thread(target=self._socket.run_forever)
            self._socket_thread.start()

            if self._reconnect_thread is None:
                self._reconnect_thread = Thread(target=self._reconnect_handler)
                self._reconnect_thread.start()

            if self._debug:
                print("[socket][start] Socket Started")
        except Exception as e:
            print(e)

    def close(self):
        if self._debug:
            print("[socket][close] Closing Socket")

        self._active = False
        try:
            self.socket.close()
        except Exception as closeError:
            if self._debug:
                print(f"[socket][close] Error while closing Socket : {closeError}")

        return


class Callbacks:
    def __init__(self, client):
        self._client = client
        self._handlers = {}

        self._methods = {
            304: self._resolve_chat_action_start,
            306: self._resolve_chat_action_end,
            1000: self._resolve_chat_message
        }

        self._chat_methods = {
            "0:0": self.on_text_message,
            "0:100": self.on_image_message,
            "0:103": self.on_youtube_message,
            "1:0": self.on_strike_message,
            "2:110": self.on_voice_message,
            "3:113": self.on_sticker_message,
            "52:0": self.on_voice_chat_not_answered,
            "53:0": self.on_voice_chat_not_cancelled,
            "54:0": self.on_voice_chat_not_declined,
            "55:0": self.on_video_chat_not_answered,
            "56:0": self.on_video_chat_not_cancelled,
            "57:0": self.on_video_chat_not_declined,
            "58:0": self.on_avatar_chat_not_answered,
            "59:0": self.on_avatar_chat_not_cancelled,
            "60:0": self.on_avatar_chat_not_declined,
            "100:0": self.on_delete_message,
            "101:0": self.on_group_member_join,
            "102:0": self.on_group_member_leave,
            "103:0": self.on_chat_invite,
            "104:0": self.on_chat_background_changed,
            "105:0": self.on_chat_title_changed,
            "106:0": self.on_chat_icon_changed,
            "107:0": self.on_voice_chat_start,
            "108:0": self.on_video_chat_start,
            "109:0": self.on_avatar_chat_start,
            "110:0": self.on_voice_chat_end,
            "111:0": self.on_video_chat_end,
            "112:0": self.on_avatar_chat_end,
            "113:0": self.on_chat_content_changed,
            "114:0": self.on_screen_room_start,
            "115:0": self.on_screen_room_end,
            "116:0": self.on_chat_host_transfered,
            "117:0": self.on_text_message_force_removed,
            "118:0": self.on_chat_removed_message,
            "119:0": self.on_text_message_removed_by_admin,
            "120:0": self.on_chat_tip,
            "121:0": self.on_chat_pin_announcement,
            "122:0": self.on_voice_chat_permission_open_to_everyone,
            "123:0": self.on_voice_chat_permission_invited_and_requested,
            "124:0": self.on_voice_chat_permission_invite_only,
            "125:0": self.on_chat_view_only_enabled,
            "126:0": self.on_chat_view_only_disabled,
            "127:0": self.on_chat_unpin_announcement,
            "128:0": self.on_chat_tipping_enabled,
            "129:0": self.on_chat_tipping_disabled,
            "65281:0": self.on_timestamp_message,
            "65282:0": self.on_welcome_message,
            "65283:0": self.on_invite_message
        }

        self._chat_actions_start = {
            "Typing": self.on_user_typing_start,
        }

        self._chat_actions_end = {
            "Typing": self.on_user_typing_end,
        }

    def _resolve_chat_message(self, data):
        key = f"{data['o']['chatMessage']['type']}:{data['o']['chatMessage'].get('mediaType', 0)}"
        return self._chat_methods.get(key, self.default)(data)

    def _resolve_chat_action_start(self, data):
        key = data['o'].get('actions', 0)
        return self._chat_actions_start.get(key, self.default)(data)

    def _resolve_chat_action_end(self, data):
        key = data['o'].get('actions', 0)
        return self._chat_actions_end.get(key, self.default)(data)

    def resolve(self, data):
        data = loads(data)
        return self._methods.get(data["t"], self.default)(data)

    def _call(self, type, data):
        if type in self._handlers:
            for handler in self._handlers[type]:
                handler(data)

    def event(self, type):
        def registerHandler(handler):
            if type in self._handlers:
                self._handlers[type].append(handler)
            else:
                self._handlers[type] = [handler]
            return handler

        return registerHandler

    def on_text_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_image_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_youtube_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_strike_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_sticker_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_not_answered(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_not_cancelled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_not_declined(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_video_chat_not_answered(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_video_chat_not_cancelled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_video_chat_not_declined(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_avatar_chat_not_answered(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_avatar_chat_not_cancelled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_avatar_chat_not_declined(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_delete_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_group_member_join(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_group_member_leave(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_invite(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_background_changed(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_title_changed(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_icon_changed(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_start(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_video_chat_start(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_avatar_chat_start(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_end(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_video_chat_end(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_avatar_chat_end(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_content_changed(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_screen_room_start(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_screen_room_end(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_host_transfered(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_text_message_force_removed(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_removed_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_text_message_removed_by_admin(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_tip(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_pin_announcement(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_permission_open_to_everyone(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_permission_invited_and_requested(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_voice_chat_permission_invite_only(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_view_only_enabled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_view_only_disabled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_unpin_announcement(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_tipping_enabled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_chat_tipping_disabled(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_timestamp_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_welcome_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_invite_message(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)

    def on_user_typing_start(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)
    def on_user_typing_end(self, data): self._call(getframe(0).f_code.co_name, Event(data["o"]).Event)

    def default(self, data): self._call(getframe(0).f_code.co_name, data)
