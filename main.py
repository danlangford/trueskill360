import trueskill
from trueskill import TrueSkill, Rating
from flask import request
from flask.ext.api import FlaskAPI, status, exceptions

# global FLASK setup
app = FlaskAPI(__name__)
app.config['DEBUG'] = True

# global TRUESKILL setup
trueskill.setup(backend='mpmath')

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

@app.route('/test')
def hello():

    msg='Hello World!\n'

    payload = {'teams':[{'alice':{}},{'bob':{}}]}

    # environment
    t = TrueSkill(backend='mpmath')

    def new_repr(self):
        return '(mu=%.3f, sigma=%.3f, exposure=%.3f)' % (self.mu, self.sigma, t.expose(self))
    Rating.__repr__ = new_repr

    # pre-match we build the teams and players
    teams = []
    for team in payload.get('teams'):
        players = {}
        for name, data in team.iteritems():
            players[name] = Rating(mu=data.get('mu'),sigma=data.get('sigma'))
        teams.append(players)

    msg += '{}'.format(teams) + '\n'

    # and assess the quality of the matchup
    quality = t.quality(teams)
    fair = not (quality<.5)
    msg += '{:.1%} chance to tie. {}'.format(quality, 'game on!' if fair else 'this may be a stomp') + '\n'

    #
    # # # # MATCH IS PLAYED
    #

    msg += "the match was won by {}".format(teams[0].keys()) + '\n'

    # post match we get new rating on the results (winner=rank 0, loser=rank 1), so alice wins this time

    diffmu1 = teams[1]['bob'].mu
    diffexposure1 = teams[1]['bob'].exposure

    teams = t.rate(teams)

    diffmu1 = teams[1]['bob'].mu - diffmu1
    diffexposure1 = teams[1]['bob'].exposure - diffexposure1

    print 'after first match the mu diff is {} and the exposure diff is {}'.format(diffmu1,diffexposure1)

    for _ in xrange(1000):
        teams = t.rate(teams)


    diffmu2 = teams[1]['bob'].mu
    diffexposure2 = teams[1]['bob'].exposure

    teams = t.rate(teams)

    diffmu2 = teams[1]['bob'].mu - diffmu2
    diffexposure2 = teams[1]['bob'].exposure - diffexposure2

    print 'after ~1,000 matches the mu diff is {} and the exposure diff is {}'.format(diffmu2,diffexposure2)


    print 'quality={}'.format(t.quality(teams))

    for team in teams:
        for name,rating in team.iteritems():
            rating.realexposure = t.expose(rating)

    msg += '{}'.format(teams) + '\n'

    """Return a friendly HTTP greeting."""
    return '<pre>\n'+msg+'\n</pre>'


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404


@app.route('/api/v1/quality/1vs1', methods=['GET','POST'])
def quality_1vs1():
    """
    hello <b>world</b>
    ### i like cheese
    \n
    any way to ` make ` a new line?
    :return:
    """
    if request.method=='GET':
        raise ExamplePayload(example={'alice':{},'bob':{}})
    players, names, _ = get_1vs1_players()
    quality = trueskill.quality_1vs1(players[names[0]], players[names[1]])
    return {'quality':quality}

@app.route('/api/v1/rate/1vs1', methods=['GET','POST'])
def rate_1vs1():
    if request.method=='GET':
        raise ExamplePayload(example={
            "bob": {
                "mu": 20.604168307008482,
                "sigma": 7.17147580700922,
                "result": "win",
            },
            "alice": {
                "mu": 29.39583169299151,
                "sigma": 7.17147580700922
            }
        })
    players, names, results = get_1vs1_players()
    p0, p1 = players[names[0]], players[names[1]]
    drawn = results[0] is results[1]
    if drawn:
        # winner and loser dont matter in a draw
        win_p, win_name, lose_p, lose_name = p0, names[0], p1, names[1]
    else:
        if maybe_win(results[0]):
            win_p, win_name, lose_p, lose_name = p0, names[0], p1, names[1]
        elif maybe_win(results[1]):
            win_p, win_name, lose_p, lose_name = p1, names[1], p0, names[0]
        else:
            raise exceptions.ParseError(detail='cannot parse results (win/lose/draw)')

    win_p, lose_p = trueskill.rate_1vs1(win_p, lose_p, drawn=drawn)
    (p0, p1) = (win_p, lose_p) if names[0] is win_name else (lose_p,win_p)
    return {names[0]:rating_json(p0,results[0]), names[1]:rating_json(p1, results[1])}

def get_1vs1_players():
    players = request.data
    names = players.keys()
    if len(names) is not 2:
        raise exceptions.ParseError(detail='request must contain exactly 2 players')
    if names[0] is names[1]:
        raise exceptions.ParseError(detail='player names/ids must be distinquishable')

    results = []

    for name in names:
        results.append(players[name].get('result'))
        players[name] = Rating(mu=players[name].get('mu'), sigma=players[name].get('sigma'))

    return players, names, results

def maybe_win(r):
    """
    inspect a result to determine a win
    :param r: result of any type
    :return: test result
    :rtype: bool
    """
    return str(r).lower() in ['1', 'true', 'win', 'winner']

def rating_json(rating, result):
    """
    Convert a Rating into something more JSON serializeable, includes 'exposure' data
    :type rating: Rating
    :param rating: the rating to convert
    :param result: the result sent in initial payload
    :rtype: dict
    :return: dict
    """
    return {'mu':rating.mu,
            'sigma':rating.sigma,
            'exposure':trueskill.expose(rating),
            'result': result}

class ExamplePayload(exceptions.APIException):
    status_code = 299
    detail = 'Example Payload.'
    def __init__(self, example=None):
        if example is not None:
            self.detail = {'example payload':example}


if __name__ == "__main__":
    app.run()