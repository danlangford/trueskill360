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
    swag = swagger(app, )
    swag['info']['version'] = 'v1'
    swag['info']['title'] = 'trueskill360'
    swag['info']['description'] = '''

    a webservice wrapping the open source trueskill.org library
    NOTE: this api does not persist data

    _mu_ = ~skill (or lower boundary of skill)
    _sigma_ = uncertainty that _mu_ is correct
    _exposure_ = leaderboard sort key. considers skill (_mu_) and
                confidence that skill is correct (_sigma_)

    STORE ALL THESE VALUES WITH HIGH PRECISION
    DO NOT ATTEMPT TO ADJUST THESE VALUES
    IF YOU HAVE A STORED _mu_ AND _sigma_ FOR A PLAYER YOU MUST SEND THEM
    OR WE WILL ASSUME ITS A NEW PLAYER WITH DEFAULT ENTRY SKILL

    order leaderboards by _exposure_ DESC.
    the more matches are played the lower `sigma` falls.
    the more `sigma` falls over time `exposure` trends upward.
    this means that the person with more games (higher confidence in _mu_) will be placed slightly higher
      on leaderboard than somebody who may have same skill but a lower confidence that its correct.

    _quality_ = 0f-1f chance the match will draw. high quality is a "even" match. low quality is a stomp
    _probability_ = .5f-1f chance the _favor_ed player will win.
                    high prob is a stomp, low prob is a "even" match
    _favor_ = player with the higher _exposure_

    YOU MAY MULTIPLY _quality_ AND _probability_ BY 100
    TO GET AN EASIER TO READ PERCENTAGE (i.e. 73% chance to win)

    '''
    return jsonify(swag)

@app.route('/test')
def test():

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
        teams = [teams[1],teams[0]]
        teams = t.rate(teams)
        print 'quality={:.1%}'.format(t.quality(teams))


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
    returns the `quality` (probably not useful to you), and the `probability` that the `favor`ed player will win.
    this is used in a pre-match scenario to see who the match thinks will will or to determine if two players are a good match for each other
    if you are using this for matchmaking you want `quality` to be towards `1.0` which is the same as `probability` towards `0.50`
    `favor` will be null if each players `exposure` is identical
    if this is a players first match just send in no addition info i.e. `{"alice"{},"bob":{}}`
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
    quality, probability, favor = quality_and_probability(players, names)
    return jsonify({
        names[0]:quality_json(players[names[0]]),
        names[1]:quality_json(players[names[1]]),
        'quality':quality,
        'probability':probability,
        'favor':favor
    })

@app.route('/api/v1/rate/1vs1', methods=['POST'])
def rate_1vs1():
    """
    rate players as result of head-to-head matchup
    returns the new rating (`mu`,`sigma`,`exposure`) of the players as a result of the match
    there must be present at least one `result` property with a value like `1` or `"win"` or `"winner"`
    denote a draw/tie with both players' `result`s the same (`"lose"`vs`"lose"` or `"draw"`vs`"draw"`, or `"tie"`vs`"tie"` or `0`vs`0`)
    response will also contain the quality information as it stood evaluated `prematch` and `postmatch`
    if the player who was `favor`ed in `prematch` was not the winner then the match was an upset or surprise (large or small)
    the `postmatch` is a quality assessment if these two players were to immediately rematch
    if this is a players first match just send in no addition info i.e. `{"alice"{"result":1},"bob":{}}`
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

    # determine pre-match quality/probability
    pre_qual, pre_prob, pre_favor = quality_and_probability(players, names)

    drawn = results[0] is results[1]
    if drawn:
        if not results[0]:
            raise InvalidAPIUsage('cannot parse results (win/lose/draw)', status_code=400)

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

    # determine post-match quality/probability
    post_qual, post_prob, post_favor = quality_and_probability({names[0]:p0, names[1]:p1}, names)

    return jsonify({
        names[0]:rate_json(p0, results[0]),
        names[1]:rate_json(p1, results[1]),
        'prematch': {
            'quality':pre_qual,
            'probability':pre_prob,
            'favor':pre_favor
        },
        'postmatch':{
            'quality':post_qual,
            'probability':post_prob,
            'favor':post_favor
        }
    })

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

def quality_and_probability(players, names):
    p0, p1 = players[names[0]], players[names[1]]
    quality = trueskill.quality_1vs1(p0, p1)
    probability = arduino_map((1-quality)*100, 0, 100, 50, 100)/100
    ex0, ex1 = trueskill.expose(p0), trueskill.expose(p1)
    if ex0 == ex1:
        favor = None
    elif ex0>ex1:
        favor = names[0]
    else:
        favor = names[1]

    return quality, probability, favor

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


def arduino_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min + 1) / (in_max - in_min + 1) + out_min


if __name__ == "__main__":
    app.run(debug=True, port=8080)
    #test()