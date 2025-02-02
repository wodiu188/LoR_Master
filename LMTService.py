#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import Models
from Models.process import updateStatus
import threading
import time
from Models.leaderboard import Leaderboard
from Models.setting import Setting
from Models.local import Local
from Models.riot import Riot
from Models.network import Network
from Models.player import Player
from Models.setting import Server
from Models.cache import Cache
from Models import master
import json
from flask import Flask, jsonify
from sentry_sdk.integrations.flask import FlaskIntegration
import sentry_sdk
import io
import sys
import constants

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
print('utf8 string test: ', '卡尼能布恩', '째남모')

sentry_sdk.init(
    "https://1138a186a6384b00a20a6196273c3009@o958702.ingest.sentry.io/5907306",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
    debug=True,
    release=constants.VERSION_NUM
)

sentry_sdk.set_context("info", {
    "version": constants.VERSION_NUM
})


master.startMasterWorker()
leaderboardModel = Leaderboard()
cacheModel = Cache()

settingInspect = Setting()
networkInspect = Network(settingInspect)
riotInspect = Riot(networkInspect, cacheModel)
playerInspect = Player(riotInspect, leaderboardModel)
localInspect = Local(settingInspect)

settingTrack = Setting()
networkTrack = Network(settingTrack)
riotTrack = Riot(networkInspect, cacheModel)
playerTrack = Player(riotTrack, leaderboardModel)
localTrack = Local(settingTrack)


class FlaskApp(Flask):
    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)
        self.processWork()
        self.leaderboardsWork()

    def processWork(self):
        def run_work():
            while True:
                updateStatus(settingTrack)
                time.sleep(3)
        work = threading.Thread(target=run_work)
        work.daemon = True
        work.start()

    def leaderboardsWork(self):
        def run_work():
            while True:
                leaderboardModel.updateAll()
                time.sleep(600)
        work = threading.Thread(target=run_work)
        work.daemon = True
        work.start()


app = FlaskApp(__name__)


@app.route("/process", methods=['get'])
def process():
    process_info = {}
    process_info['server'] = settingTrack.riotServer
    process_info['port'] = settingTrack.port
    return jsonify(process_info)


@app.route("/track", methods=['get'])
def track():
    return jsonify(localTrack.updateStatusFlask())


@app.route("/history/<string:server>/<string:name>/<string:tag>", methods=['get'])
def history(server, name, tag):
    if server == 'sea':
        print('history: Riot API not suppport SEA')
        return jsonify([])
    settingInspect.riotServer = Server._value2member_map_[server]
    playerInspect.inspectFlask(name, tag, 10)
    playerInspect.loadMatchsToFlask()
    return jsonify(playerInspect.historyFlask.__dict__['history'])


@app.route("/name/<string:server>/<string:playername>", methods=['get'])
def get_names(server, playername):
    playernames = set()
    try:
        with open('data/' + server.lower() + '.json', 'r', encoding='utf-8') as fp:
            names = json.load(fp)
            for name in names.items():
                playernames.add(name[0] + '#' + name[1])
    except Exception as e:
        print('updatePlayernames', e)
    playerList = set()
    for name in playernames:
        if name[0:len(playername)].lower() == playername.lower():
            playerList.add(name)
    returnList = jsonify(list(playerList))
    return returnList


@app.route("/search/<string:server>/<string:name>/<string:tag>", methods=['get'])
def search(name, tag, server):
    settingModel = Setting()
    settingModel.riotServer = Server._value2member_map_[server]
    maxNum = constants.MAX_NUM_INSPECT
    if (name + '#' + tag).lower() == settingTrack.playerId.lower():
        maxNum = 20
    riotModel = Riot(Network(settingModel), cacheModel)
    playerModel = Player(riotModel, leaderboardModel)
    playerModel.inspectFlask(name, tag, maxNum)
    inspection = {}
    inspection['history'] = playerModel.historyFlask.__dict__['history']
    inspection['matches'] = playerModel.matchesJson
    return jsonify(playerModel.matchesJson)


@app.route("/leaderboard/<string:server>", methods=['get'])
def get_leaderboard(server):
    # refactor to leaderboard model
    board = leaderboardModel.getLeaderboard(server)

    boardWithTag = []
    playlistDict = {}

    if board is None:
        return jsonify(boardWithTag)

    try:
        with open('data/' + server + '.json', 'r', encoding='utf-8') as fp:
            playlistDict = json.load(fp)
    except Exception as e:
        print('Restful: unable to load player list')
    for player in board:
        if player['name'] in playlistDict:
            player['tag'] = playlistDict[player['name']]
        else:
            player['tag'] = ''
        boardWithTag.append(player)
    return jsonify(boardWithTag)


@app.route("/version", methods=['get'])
def get_version():
    import requests
    version = {}
    version['version'] = constants.VERSION_NUM
    version['remoteVersion'] = constants.VERSION_NUM
    try:
        response = requests.get(
            "https://api.github.com/repos/shaobaili3/LoR_Master/releases/latest")
        githubJson = response.json()
    except Exception as e:
        print('get_version() error', e)
        return jsonify(version)
    version['remoteVersion'] = githubJson['tag_name']
    version['downloadUrl'] = githubJson['assets'][0]['browser_download_url']
    version['github'] = githubJson
    return jsonify(version)


@app.route("/opInfo", methods=['get'])
def opInfo():
    opInfo = {}
    localTrack.updateTagByName(
        localTrack.positional_rectangles['OpponentName'])
    opInfo['name'] = localTrack.positional_rectangles['OpponentName']
    opInfo['tag'] = localTrack.opponentTag
    opInfo['rank'], opInfo['lp'] = leaderboardModel.checkRank(
        opInfo['name'], settingTrack.riotServer)
    return jsonify(opInfo)


@app.route("/status", methods=['get'])
def get_status():
    status = {}
    status['playerId'] = settingTrack.playerId
    status['port'] = settingTrack.port
    status['server'] = settingTrack.riotServer
    status['language'] = settingTrack.language
    status['lorRunning'] = settingTrack.isLorRunning
    return jsonify(status)


app.run(port=63312, debug=True, use_reloader=False)
