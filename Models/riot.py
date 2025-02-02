import Models.network
import requests
import json
import os
import constants


class Riot:
    def __init__(self, network, cache):
        self.network = network
        self.cache = cache
        self.cache.loadJson()
        self.session = requests.Session()
        return

    def getPlayerPUUID(self, name, tag):
        # Developer keys expose in cache. 'lower()' make sure link will not change by case sensitivity.
        puuidLink = self.network.getPUUID(name.lower(), tag.lower())
        if puuidLink in self.cache.riotIds:
            return self.cache.riotIds[puuidLink]
        print(puuidLink)
        try:
            puuidRequest = self.session.get(puuidLink)
        except requests.exceptions.RequestException as e:
            print(puuidLink)
            print('getPlayerPUUID error": ', e)
            return None
        idDetails = puuidRequest.json()
        header = puuidRequest.headers
        if not puuidRequest.ok:
            print('getPlayerPUUID server error:', puuidLink)
            print(puuidRequest.headers)
            print(puuidRequest.status_code)
            print(idDetails)
            if 'Retry-After' in header:
                print('getPlayerPUUID server busy',
                      header['Retry-After'], 'seconds')
                Models.network.switchAPI()
            return None
        else:
            # For some special account, playerId->puuid only return puuid without name and tag
            puuid = idDetails.get('puuid')
            gameName = idDetails.get('gameName')
            tagLine = idDetails.get('tagLine')
            if gameName is None or tagLine is None:
                gameName = name
                tagLine = tag
                # give up saving cache for this special case
                print(gameName, '#' , tagLine, ': only return puuid without name and tag!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                return puuid
            if puuid is not None:
                self.cache.riotIds[puuidLink] = puuid
                self.cache.playerNames[puuid] = gameName, tagLine
                self.cache.save()
            return puuid

    def saveMatchIdsInCache(self, puuid, matchIds):
        playName = self.getPlayerName(puuid)
        server = self.network.setting.riotServer
        uniqueName = playName[0] + playName[1] + server
        matchIdsCache = self.cache.matches.get(uniqueName)
        if matchIdsCache is not None:
            new = matchIds + list(set(matchIdsCache) - set(matchIds))
            self.cache.matches[uniqueName] = new
        else:
            self.cache.matches[uniqueName] = matchIds
        os.makedirs('data', exist_ok=True)
        with open('data/matches.json', 'w+', encoding='utf-8') as fp:
            json.dump(self.cache.matches, fp)

    def getMatchesInCache(self, puuid):
        playName = self.getPlayerName(puuid)
        server = self.network.setting.riotServer
        uniqueName = playName[0] + playName[1] + server
        return self.cache.matches[uniqueName]

    def getMatches(self, puuid, saveCache=True):
        matchLink = self.network.getMatchesLink(puuid)
        try:
            matchRequest = self.session.get(matchLink)
        except requests.exceptions.RequestException as e:
            print(matchLink)
            print('getMatches error: ', e)
            return None
        matchIds = matchRequest.json()
        header = matchRequest.headers
        if not matchRequest.ok:
            print('getmatches server error:', matchLink)
            print(matchLink)
            print(matchRequest.headers)
            print(matchRequest.status_code)
            print(matchIds)
            if 'Retry-After' in header:
                print('getmatches server busy',
                      header['Retry-After'], 'seconds')
                Models.network.switchAPI()
            return None
        if saveCache:
            self.saveMatchIdsInCache(puuid, matchIds)
            return self.getMatchesInCache(puuid)
        return matchIds

    def getDetail(self, matchId, matchIndex=1, max_num=constants.MAX_NUM_ALL):
        # If matchIndex bigger than MAX, only pull data from cache
        if matchId in self.cache.matchDetails or matchIndex > max_num - 1:
            return self.cache.matchDetails.get(matchId)
        detailsLink = self.network.getDetailsLink(matchId)
        try:
            detailsRequest = self.session.get(detailsLink)
        except requests.exceptions.RequestException as e:
            print(detailsLink)
            print(e)
            print('getDetail error', e)
            return None
        detail = detailsRequest.json()
        header = detailsRequest.headers
        if 'X-Method-Rate-Limit-Count' in header:
            print('X-Method-Rate-Limit-Count: ',
                  header['X-Method-Rate-Limit-Count'])
            print('X-App-Rate-Limit', header['X-App-Rate-Limit'])
        if not detailsRequest.ok:
            print('getDetail server error:', detailsLink)
            print(header)
            print(detailsRequest.status_code)
            print(detail)
            if 'Retry-After' in header:
                print('getDetail server busy APIKEY: ', Models.network.API_KEY, header['Retry-After'], 'seconds')
                Models.network.switchAPI()
                return None
            return None
        else:
            self.cache.matchDetails[matchId] = detail
            self.cache.save()
        if detail is None:
            print('match id:', matchId , 'details empty')
        return detail

    def getPlayerName(self, puuid):
        if puuid in self.cache.playerNames:
            return self.cache.playerNames[puuid]
        nameLink = self.network.getNameLink(puuid)
        try:
            nameRequest = self.session.get(nameLink)
        except requests.exceptions.RequestException as e:
            print(nameLink)
            print(e)
            print('getPlayerName error')
            return 'Error', 'Unknow'
        name = nameRequest.json()
        header = nameRequest.headers
        if not nameRequest.ok:
            print('getPlayerName server error:', nameLink)
            print(header)
            print(nameRequest.status_code)
            print(name)
            if 'Retry-After' in header:
                print('Riot server is busy', header['Retry-After'], 'second')
                Models.network.switchAPI()
            return 'Unknow', str(puuid)[0:5]
        else:
            self.cache.playerNames[puuid] = name['gameName'], name['tagLine']
            self.cache.save()
        return name['gameName'], (name['tagLine'])
