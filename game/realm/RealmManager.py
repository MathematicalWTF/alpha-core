import socketserver
import threading
import socket

from struct import pack

from game.world.WorldSessionStateHandler import WorldSessionStateHandler
from utils.ConfigManager import config
from utils.Logger import Logger
from network.packet.PacketWriter import *


class ThreadedLoginServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class LoginServerSessionHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.serve_realm(self.request)
        finally:
            self.request.shutdown(socket.SHUT_RDWR)
            self.request.close()

    @staticmethod
    def serve_realm(sck):
        name_bytes = PacketWriter.string_to_bytes(config.Server.Connection.RealmServer.realm_name)
        address_bytes = PacketWriter.string_to_bytes(('%s:%s' % (config.Server.Connection.RealmProxy.host,
                                                                 config.Server.Connection.RealmProxy.port)))

        # TODO: Should probably move realms to database at some point, instead of config.yml
        packet = pack(
            '<B%us%usI' % (len(name_bytes), len(address_bytes)),
            1,  # Number of realms
            name_bytes,
            address_bytes,
            # I assume this number is meant to show current online players since there is
            # no way of knowing the account yet when realmlist is requested in 0.5.3.
            WorldSessionStateHandler.get_process_shared_session_number()
        )

        Logger.debug('[%s] Sending realmlist...' % sck.getpeername()[0])
        sck.sendall(packet)

    @staticmethod
    def start():
        Logger.success('Login server started.')

        ThreadedLoginServer.allow_reuse_address = True
        with ThreadedLoginServer((config.Server.Connection.RealmServer.host,
                                  config.Server.Connection.RealmServer.port), LoginServerSessionHandler) \
                as login_instance:
            try:
                login_session_thread = threading.Thread(target=login_instance.serve_forever())
                login_session_thread.daemon = True
                login_session_thread.start()
            except KeyboardInterrupt:
                Logger.info("Login server turned off.")


class ThreadedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class ProxyServerSessionHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.redirect_to_world(self.request)
        finally:
            self.request.shutdown(socket.SHUT_RDWR)
            self.request.close()

    @staticmethod
    def redirect_to_world(sck):
        world_bytes = PacketWriter.string_to_bytes(('%s:%s' % (config.Server.Connection.WorldServer.host,
                                                               config.Server.Connection.WorldServer.port)))
        packet = pack(
            '<%us' % len(world_bytes),
            world_bytes
        )

        Logger.debug('[%s] Redirecting to world server...' % sck.getpeername()[0])
        sck.sendall(packet)

    @staticmethod
    def start():
        Logger.success('Proxy server started.')

        ThreadedProxyServer.allow_reuse_address = True
        with ThreadedProxyServer((config.Server.Connection.RealmServer.host,
                                  config.Server.Connection.RealmProxy.port), ProxyServerSessionHandler) \
                as proxy_instance:
            try:
                proxy_session_thread = threading.Thread(target=proxy_instance.serve_forever())
                proxy_session_thread.daemon = True
                proxy_session_thread.start()
            except KeyboardInterrupt:
                Logger.info("Proxy server turned off.")

