import os
from unittest import TestCase
from models import db, connect_db, Message, User, Likes

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app

db.create_all()


class MessageModelTestCase(TestCase):
    """Test models for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        #Setting up a user.
        u = User.signup("testing", "testing@test.com", "password", None)
        self.uid = 4444
        u.id = self.uid
        db.session.commit()

        self.u = User.query.get(self.uid)

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does basic model work?"""

        m = Message(text='Hello', user_id=self.uid)

        db.session.add(m)
        db.session.commit()

        # User should have 1 messages
        self.assertEqual(len(self.u.messages), 1)
        self.assertEqual(self.u.messages[0].text, 'Hello')

#########################

    def test_message_likes(self):
        """Is # of likes correct?"""
        m1 = Message(text='Hello', user_id=self.uid)
        m2 = Message(text='Funny', user_id=self.uid)

        u2 = User.signup('user2', 'test2@gmail.com', 'password', None)
        uid = 5555
        u2.id = uid
        db.session.add_all([m1, m2, u2])
        db.session.commit()

        u2.likes.append(m1)

        db.session.commit()

        like = Likes.query.filter(Likes.user_id == uid).all()
        self.assertEqual(len(like), 1)
        self.assertEqual(like[0].message_id, m1.id)



   