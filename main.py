import trueskill
from trueskill import TrueSkill, Rating
from flask import Flask, request, jsonify
from flask_swagger import swagger

# global FLASK setup
app = Flask(__name__, static_url_path='')
app.config['DEBUG'] = True

# global TRUESKILL setup
trueskill.setup(backend='mpmath')

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

class InvalidAPIUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route("/spec")
def spec():
    swag = swagger(app)
    swag['info']['version'] = 'v1'
    swag['info']['title'] = 'trueskill360'
    return jsonify(swag)

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

@app.errorhandler(InvalidAPIUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route('/api/v1/quality/1vs1', methods=['POST'])
def quality_1vs1():
    """
    test the quality of a head-to-head matchup
    ---
    tags:
      - 1vs1
    parameters:
      - in: body
        name: body
        description: two players and their current trueskill360 info
        schema:
          type: object
          example: |
            {
                "alice": {
                    "mu": 20.604168307008482,
                    "sigma": 7.17147580700922
                },
                "bob": {
                    "mu": 29.39583169299151,
                    "sigma": 7.17147580700922
                }
            }

    responses:
      201:
        description: your payload with quality property added
      400:
        description: bad request most commonly from not sending exactly 2 players or not having their names be unique

    """
    players, names, _ = get_1vs1_players()
    quality = trueskill.quality_1vs1(players[names[0]], players[names[1]])
    return jsonify({names[0]:quality_json(players[names[0]]), names[1]:quality_json(players[names[1]]), 'quality':quality})

@app.route('/api/v1/rate/1vs1', methods=['POST'])
def rate_1vs1():
    """
    rate players as result of head-to-head matchup
    ---
    tags:
      - 1vs1
    parameters:
      - in: body
        name: body
        description: two players and their current trueskill360 info
        schema:
          type: object
          example: |
            {
                "alice": {
                    "mu": 20.604168307008482,
                    "sigma": 7.17147580700922,
                    "result": "win"
                },
                "bob": {
                    "mu": 29.39583169299151,
                    "sigma": 7.17147580700922
                }
            }

    responses:
      201:
        description: the two players with new rating info
      400:
        description: bad request most commonly from not sending exactly 2 players or not having their names be unique

    """
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
            raise InvalidAPIUsage('cannot parse results (win/lose/draw)', status_code=400)

    win_p, lose_p = trueskill.rate_1vs1(win_p, lose_p, drawn=drawn)
    (p0, p1) = (win_p, lose_p) if names[0] is win_name else (lose_p,win_p)
    return jsonify({names[0]:rate_json(p0,results[0]), names[1]:rate_json(p1, results[1])})

def get_1vs1_players():
    players = request.get_json()
    names = players.keys()
    if len(names) is not 2:
        raise InvalidAPIUsage('request must contain exactly 2 players', status_code=400)
    if names[0] is names[1]:
        raise InvalidAPIUsage('player names/ids must be distinquishable', status_code=400)

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

def quality_json(rating):
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
            'exposure':trueskill.expose(rating)}

def rate_json(rating, result):
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



if __name__ == "__main__":
    app.run(debug=True)