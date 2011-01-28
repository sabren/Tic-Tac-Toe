from django.db import models as m
from django.contrib.auth.models import User
Q = m.Q

qUnfinished = lambda : Q(finished=False)
qNeedsPlayer = lambda : Q(player1=None) | Q(player2=None)
qHas2Players = lambda : ~qNeedsPlayer()
qForUser = lambda u: Q(player1=u) | Q(player2=u)

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
    nextPlayer = m.IntegerField(default=1, choices=((1, 'player1'), (2, 'player2')))
    finished = m.BooleanField(default=False)
    winner = m.ForeignKey(User, related_name='winner', null=True)

    def __str__(self):
        return '#%i : %s vs %s' % (
            self.id,
            self.player1.username if self.player1 else '?',
            self.player2.username if self.player2 else '?')

    @property
    def toPlay(self):
        return self.player1 if self.nextPlayer == 1 else self.player2


    @classmethod
    def findAllFor(cls, user):
        return cls.objects.filter(qForUser(user))

    @classmethod
    def findActiveFor(cls, user):
        return cls.objects.filter(
                qForUser(user) & qHas2Players() & qUnfinished())

    @classmethod
    def findPendingFor(cls, user):
        return cls.objects.filter(
                qForUser(user) & ~qHas2Players())

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

    