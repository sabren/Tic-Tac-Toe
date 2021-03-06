from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.testcases import TestCase
from DJTickyTack.models import Game
from settings import kGames, kJoin, kLogin, kLogout, kRoot

# so we can inspect generated SQL via connection.queries:
from django.db import connection
from django.conf import settings

settings.DEBUG = True

def urlOf(viewName):
    return reverse('DJTickyTack.views.%s' % viewName)


class BaseTest(TestCase):
    """
    Defines a shared test fixture.
    """
    def setUp(self):
        create = User.objects.create_user
        self.playerA = create('playerA', 'playerA@example.com', 'pwA')
        self.playerB = create('playerB', 'playerB@example.com', 'pwB')


class GameTest(BaseTest):
    def test_construct(self):
        """
        A Game is a match between two players, started at a particular time.
        """
        game = Game(player1=self.playerA, player2=self.playerB)

        # player 1 to play
        self.assertEquals(self.playerA, game.toPlay)

        # auto-populate the date on save
        self.assertEquals(None, game.startedOn)
        game.save()
        self.assertNotEqual(None, game.startedOn)


    def test_asGrid(self):
        game = Game()
        grid = game.asGrid()
        self.assertEquals(3, len(grid))
        self.assertEquals(3, len(grid[0]))



class SiteTest(BaseTest):

    def setUp(self):
        """
        Create two players and a game between them.
        """
        super(SiteTest, self).setUp()
        self.game = Game(player1=self.playerA, player2=self.playerB)
        self.game.save()
        self.client = Client()
        self.client.login(username='playerA', password='pwA')


    def test_games(self):
        """
        The games page lists your active games.
        """
        c = self.client

        # it is our turn, so we should see the active game:
        r = c.get(kGames)
        self.assertEquals(1, len(r.context['activeGames']))

        # there are no pending games yet:
        self.assertEquals(0, len(r.context['pendingGames']))

        # create two more games:
        c.post(kGames, {'playAs':'X'})
        c.post(kGames, {'playAs':'O'})

        # now we have one active game and two pending games
        r = c.get(kGames)
        self.assertEquals(1, len(r.context['activeGames']))
        self.assertEquals(2, len(r.context['pendingGames']))


    def test_join(self):
        """
        Only games created by others that don't yet have a
        second player should be playable.
        """
        pAx = Game.createFor(self.playerA, playAs='X')
        pBx = Game.createFor(self.playerB, playAs='X')
        pBo = Game.createFor(self.playerB, playAs='O')

        # since we're logged in as player A, the two games started
        # by player B should be joinable
        r = self.client.get(kJoin)
        joinable = list(r.context['joinable'])
        self.failIf(pAx in joinable)
        self.assertTrue(pBx in joinable)
        self.assertTrue(pBo in joinable)
        self.assertEquals(2, len(joinable))

        # join player B's game as the new player X
        r = self.client.post(kJoin + str(pBo.id))
        self.assertTrue(r.has_header('Location'))
        # sure would be nice if reverse(views.games) worked here :/
        self.assertTrue(r['Location'].endswith(urlOf('games')))

        # the fixture has one active game, and we just joined another.
        # we should have two active games.
        r = self.client.get(kGames)
        self.assertEquals(2, len(r.context['activeGames']))
        self.assertEquals(1, len(r.context['pendingGames']))

        # join the other game, but it will be pending rather than
        # active because it isn't our turn.
        r = self.client.post(kJoin + str(pBx.id))
        r = self.client.get(kGames)
        self.assertEquals(2, len(r.context['activeGames'])) # same
        self.assertEquals(2, len(r.context['pendingGames'])) # +1


    def test_move(self):
        self.assertEquals(0, len(self.game.moves.all()))
        r = self.client.post(kGames + str(self.game.id), {'move': 'XB2'})
        self.game = Game.objects.get(pk=self.game.id) # no .reload() :/
        self.assertEquals(1, len(self.game.moves.all()))
    