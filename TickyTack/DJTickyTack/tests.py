from django.contrib.auth.models import User
from django.test.client import Client
from django.test.testcases import TestCase
from DJTickyTack.models import Game
import urls

# so we can inspect generated SQL via connection.queries:
from django.db import connection
from django.conf import settings
settings.DEBUG = True


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
        A Game is a match between two players, started on a particular date.
        """
        game = Game(player1=self.playerA, player2=self.playerB)

        # player 1 to play
        self.assertEquals(self.playerA, game.toPlay)

        # auto-populate the date on save
        self.assertEquals(None, game.startedOn)
        game.save()
        self.assertNotEqual(None, game.startedOn)



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

        # at first, we should see the active game:
        r = c.get(urls.kGames)
        self.assertEquals(1, len(r.context['activeGames']))

        # there are no pending games yet:
        self.assertEquals(0, len(r.context['pendingGames']))

        # create two more games:
        c.post(urls.kGames, {'playAs':'X'})
        c.post(urls.kGames, {'playAs':'O'})

        # now we have one active game and two pending games
        r = c.get(urls.kGames)
        self.assertEquals(1, len(r.context['activeGames']))
        self.assertEquals(2, len(r.context['pendingGames']))


    def test_join(self):
        """
        Only games created by others that don't yet have a
        second player should be playable.
        """
        p1x = Game.createFor(self.playerA, playAs='X')
        p2x = Game.createFor(self.playerB, playAs='X')
        p2o = Game.createFor(self.playerB, playAs='O')

        r = self.client.get(urls.kJoin)
        joinable = list(r.context['joinable'])
        self.assertEquals(2, len(joinable))
