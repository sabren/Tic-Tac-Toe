from django.core.urlresolvers import reverse
from django.db import models as m
from django.contrib.auth.models import User
from django.db.models.expressions import F
from MinMaxMoe.tictactoe import TicTacToe
from settings import kGames

Q = m.Q

qFinished = lambda : Q(finished=True)
qNeedsPlayer1 = lambda : Q(player1=None)
qNeedsPlayer2 = lambda : Q(player2=None)
qNeedsPlayer = lambda : qNeedsPlayer1() | qNeedsPlayer2()
qHas2Players = lambda : ~qNeedsPlayer()
qForUser = lambda u: Q(player1=u) | Q(player2=u)
qToPlay = lambda u: Q(toPlay=u)

# !! logically:
# qNotUser = lambda u: ~qForUser(u)
# ... but django doesn't care about your logic. :)
qNotUser = lambda u: ~Q(player1=u) & ~Q(player2=u)


class Game(m.Model):
    """
    Represents a match between two players.
    """
    startedOn = m.DateTimeField(auto_now_add=True)
    player1 = m.ForeignKey(User, related_name='player1', null=True)
    player2 = m.ForeignKey(User, related_name='player2', null=True)
    toPlay = m.ForeignKey(User, related_name='toPlay', null=True)
    winner = m.ForeignKey(User, related_name='winner', null=True, blank=True)
    finished = m.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super(Game, self).__init__(*args, **kwargs)
        if self.player1 and self.player2 and not self.toPlay:
            self.toPlay = self.player1

    def __str__(self):
        return '#%i : %s' % (self.id, self.asVsString())

    def asVsString(self):
        return '%s vs %s' % (
            self.player1.username if self.player1 else '?',
            self.player2.username if self.player2 else '?')

    @classmethod
    def findAllFor(cls, user):
        return cls.objects.filter(qForUser(user))

    @classmethod
    def findActiveFor(cls, user):
        return cls.objects.filter(
                qForUser(user) & qToPlay(user))

    @classmethod
    def findPendingFor(cls, user):
        return cls.objects.filter(
                qForUser(user) & ~qFinished() & ~qToPlay(user))

    @classmethod
    def findFinishedFor(cls, user):
        return cls.objects.filter(
                qForUser(user) & qFinished())



    @classmethod
    def createFor(cls, user, playAs):
        game = Game()
        if playAs == 'X':
            game.player1 = user
        elif playAs == 'O':
            game.player2 = user
        else:
            raise TypeError("playAs should be 'X' or 'O', not %r" % playAs)
        game.save()
        return game

    @classmethod
    def findJoinableBy(cls, user):
        return cls.objects.filter(qNeedsPlayer() & qNotUser(user))

    @classmethod
    def tryToJoin(cls, user, gameId):
        """
        The game may already be full, so just attempt to join, and
        return True if joined, False otherwise
        """
        # We want to include the null in the where clause so we don't accidentally
        # overwrite another player's foreign key if they beat us to joining.
        # .update() returns a count, which here will always be 1 or 0
        x = cls.objects.filter(qNeedsPlayer1() & Q(id=gameId))\
            .update(player1=user, toPlay=user)
        o = cls.objects.filter(qNeedsPlayer2() & Q(id=gameId))\
            .update(player2=user, toPlay=F('player1'))
        return bool(x or o)


    # @TODO: i think game<->player should be a many to many junction table...
    @property
    def firstPlayer(self):
        return self.player2 if self.player1 is None else self.player1

    @property
    def firstPlayerRole(self):
        return 'O' if self.player1 is None else 'X'

    def asTicTacToe(self):
        t = TicTacToe()
        for move in self.moves.all():
            t = getattr(t, move.move)
        return t

    def asGrid(self):
        return self.asTicTacToe().data

    def asUrl(self):
        return kGames + str(self.id)


    def togglePlayer(self, save=False):
        self.toPlay = self.player1 if self.toPlay == self.player2\
                                   else self.player2
        if save:
            self.save()


class Move(m.Model):
    game = m.ForeignKey(Game, related_name='moves')
    player = m.ForeignKey(User)
    move = m.TextField(max_length=64) # really 3 for tic tac toe
