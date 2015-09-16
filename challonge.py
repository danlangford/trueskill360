# coding=UTF8
__author__ = 'danlangford'

import requests
import requests_cache
from keen.client import KeenClient

keen_client = KeenClient(
    project_id="aaa",
    write_key="bbb",
    read_key="zzzz",
    master_key="abcd"
)

requests_cache.install_cache('demo_cache', allowable_methods=['GET','POST'])

base_api='https://api.challonge.com/v1'
api_key='qwerty'
params={'api_key':api_key}

def doit():

    all_players_by_name = {}
    sorted_names = []

    #tournaments = requests.get(base_api+'/tournaments.json', params=params).json()
    tournaments = [
        {'tournament':{'url':'season1', 'subdomain':'hearthside'}},
        {'tournament':{'url':'season2', 'subdomain':'hearthside'}},
        {'tournament':{'url':'season3', 'subdomain':'hearthside'}},
        {'tournament':{'url':'HSCupA', 'subdomain':'hearthside'}},
        {'tournament':{'url':'HSCupB', 'subdomain':'hearthside'}},
        {'tournament':{'url':'HSCupC', 'subdomain':'hearthside'}},
        {'tournament':{'url':'HSCupD', 'subdomain':'hearthside'}},
        {'tournament':{'url':'HSCup', 'subdomain':'hearthside'}},
        {'tournament':{'url':'season4open', 'subdomain':'hearthside'}},
        {'tournament':{'url':'season4heroic', 'subdomain':'hearthside'}},
    ]

    for tournament in tournaments:
        t = tournament.get('tournament')
        url, subdomain = t.get('url'), t.get('subdomain')
        print '\n## EVENT host={} url={} \n'.format(subdomain, url)

        tournament_participants = []
        participants = requests.get(base_api+'/tournaments/{}-{}/participants.json'.format(subdomain, url), params=params).json()

        for participant in participants:
            p = participant.get('participant')
            pid, pname, display_name = p.get('id'), p.get('name'), p.get('display_name')
            tournament_participants.append(pid)
            # print 'name={} display_name={} pid={}'.format(pname, display_name, pid)
            pkey = pname.split('#')[0].lower()
            if pkey == 'drewcork':
                pkey = 'corkscrew'
            pold = all_players_by_name.get(pkey, {'key':pkey,'num':0,'pids':[]})
            all_players_by_name[pkey] = {'key':pkey, 'name':pname,'display_name':display_name, 'num':pold.get('num',0)+1, 'pids':pold.get('pids',[])+[pid], 'rating':pold.get('rating',{})}

        matches = requests.get(base_api+'/tournaments/{}-{}/matches.json'.format(subdomain, url), params=params).json()

        matches, stages = detect_multi_stage(matches)
        if stages > 1:
            matches = match_pid_mapping(matches, tournament_participants)

        ##matches.sort(key=lambda x: x['match']['started_at'])

        for match in matches:
            m = match.get('match')
            round, ident, loser_id, winner_id = m.get('round'), m.get('identifier'), m.get('loser_id'), m.get('winner_id')
            # print '{}{}: loser=({}) winner=({})'.format(round, ident, loser_id, winner_id)
            if winner_id:
                winner = [{'name':key,'rating':val.get('rating',{})} for key,val in all_players_by_name.iteritems() if winner_id in val.get('pids',[])][0]
                loser = [{'name':key,'rating':val.get('rating',{})} for key,val in all_players_by_name.iteritems() if loser_id in val.get('pids',[])][0]

                winner['rating']['result']=1
                loser['rating']['result']=0

                new_ratings = requests.post('https://trueskill360.appspot.com/api/v1/rate/1vs1', json={
                    winner['name']:winner['rating'],
                    loser['name']:loser['rating'],
                }).json()

                print 'VICTORY {} (Δ: R=+{:.1f}, μ=+{:.1f}) \t DEFEAT {} (Δ: R=-{:.1f}, μ=-{:.1f})'.format(
                    winner['name'],
                    new_ratings[winner['name']]['exposure'] - all_players_by_name[winner['name']].get('rating',{}).get('exposure',0),
                    new_ratings[winner['name']]['mu'] - all_players_by_name[winner['name']].get('rating',{}).get('mu',25),

                    loser['name'],
                    all_players_by_name[loser['name']].get('rating',{}).get('exposure',0) - new_ratings[loser['name']]['exposure'],
                    all_players_by_name[loser['name']].get('rating',{}).get('mu',25)-new_ratings[loser['name']]['mu'],
                    )
                # keen_client.add_events({'match5': [{
                #     'started_at':m['started_at'],
                #     'host': subdomain,
                #     'url': url,
                #     'match_ident': ident,
                #     'round': round,
                #     'did_win': 1,
                #     'name': winner['name'],
                #     'opponent': loser['name'],
                #     'rating': new_ratings[winner['name']],
                #     'delta': {
                #         'mu':new_ratings[winner['name']]['mu'] - all_players_by_name[winner['name']].get('rating',{}).get('mu',25),
                #         'sigma':new_ratings[winner['name']]['mu'] - all_players_by_name[winner['name']].get('rating',{}).get('sigma',8.333),
                #         'exposure':new_ratings[winner['name']]['exposure'] - all_players_by_name[winner['name']].get('rating',{}).get('exposure',0),
                #     },
                # }, {
                #     'started_at':m['started_at'],
                #     'host': subdomain,
                #     'url': url,
                #     'match_ident': ident,
                #     'round': round,
                #     'did_win': 0,
                #     'name': loser['name'],
                #     'opponent': winner['name'],
                #     'rating': new_ratings[loser['name']],
                #     'delta': {
                #         'mu':new_ratings[loser['name']]['mu'] - all_players_by_name[loser['name']].get('rating',{}).get('mu',25),
                #         'sigma':new_ratings[loser['name']]['mu'] - all_players_by_name[loser['name']].get('rating',{}).get('sigma',8.333),
                #         'exposure':new_ratings[loser['name']]['exposure'] - all_players_by_name[loser['name']].get('rating',{}).get('exposure',0),
                #     },
                # }]})

                all_players_by_name[winner['name']]['rating'] = new_ratings[winner['name']]
                all_players_by_name[loser['name']]['rating'] = new_ratings[loser['name']]


        print '\n### LEADERBOARD AFTER %s %s\n' % (subdomain, url)
        bad_players = { k: v for (k,v) in all_players_by_name.iteritems() if 'exposure' not in v['rating']}
        for b_p in bad_players:
            del all_players_by_name[b_p]

        sorted_names = sorted(all_players_by_name, key=lambda x: all_players_by_name[x]['rating']['exposure'], reverse=True)

        i = 0
        prev_ex = None
        for s_name in sorted_names:
            i=i+1
            # print '{}({:.1f})'.format(s_name, max(0,all_players_by_name[s_name]['rating']['exposure']))
            mu = all_players_by_name[s_name]['rating']['mu']
            sigma = all_players_by_name[s_name]['rating']['sigma']
            curr_ex = all_players_by_name[s_name]['rating']['exposure']
            print u'{} {} (R={:.1f}, μ={:.1f}, σ={:.1f})'.format(str(i if curr_ex != prev_ex else '   ').zfill(3), s_name.upper(), max(0,curr_ex), mu, sigma)
            prev_ex = curr_ex


    num_one_rating = all_players_by_name[sorted_names[0]]['rating']
    for s_name in sorted_names:
        if s_name != sorted_names[0]:
            qual = requests.post('https://trueskill360.appspot.com/api/v1/quality/1vs1', json={
                sorted_names[0]:num_one_rating,
                s_name:all_players_by_name[s_name]['rating'],
            }).json()
            print '{:.1%} chance that {} beats {}'.format(qual['probability'], qual['favor'], s_name if qual['favor'] == sorted_names[0] else sorted_names[0])

    print '\n#### done'

def detect_multi_stage(matches):
    stages = 0
    for match in matches:
        m = match.get('match')
        ident = m.get('identifier')
        if ident == 'A':
            stages += 1
    return matches, stages

def match_pid_mapping(matches, participants):
    participants = sorted(set(participants))
    other_ids=set()
    for match in matches:
        m = match['match']
        for e_id in ['winner_id', 'loser_id']:
            x_id = m[e_id]
            if x_id and x_id not in participants:
                other_ids.add(x_id)

    other_ids = sorted(other_ids)
    for match in matches:
        m = match['match']
        for e in ['player1_id','player2_id','loser_id','winner_id']:
            if m[e] and m[e] in other_ids:
                m[e] = participants[other_ids.index(m[e])]

    return matches


if __name__ == '__main__':
    doit()