"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test models for users."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        #Setting up user 1 and 2.
        u1 = User.signup('test1', 'email1@gmail.com', 'password', None)
        uid1 = 1111
        u1.id = uid1

        u2 = User.signup('test2', 'email2@gmail.com', 'password', None)
        uid2 = 2222
        u2.id = uid2

        db.session.commit()

        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        self.u1 = u1
        self.uid1 = uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

#########################


    # def test_user_repr(self):
    #     """Does __repr__ works correctly?"""

    #     id = self.uid1
    #     print('u1-id', self.uid1)
    #     print('u2-id', self.uid2)


    #     self.assertEqual(self.u1, f'<User \#\ id: testuser, test@test.com>')

#########################

    def test_followers(self):
        """Does # of followers correct?"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertEqual(len(self.u2.followers), 1)
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(len(self.u1.following), 1)

        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        """Does the is_following method works correctly?"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):
        """Does the is_followed_by method works correctly?"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u2.is_followed_by(self.u1))
        self.assertFalse(self.u1.is_followed_by(self.u2))

################################
    
    def test_valid_signup(self):
        """Does User.signup create a new user with valid credential?"""
        u = User.signup("testuser", "test@test.com", "password", None)
        id = 3333
        u.id = id
        db.session.commit()

        u = User.query.get(id)
        self.assertIsNotNone(u)

        self.assertEqual(u.username, 'testuser')
        self.assertEqual(u.email, 'test@test.com')
        self.assertEqual(u.image_url, '/static/images/default-pic.png')
        #This should be False because of hashing
        self.assertNotEqual(u.password, 'password')
        #Bcrypt strings start with this    
        self.assertTrue(u.password.startswith('$2b$'))

    def test_invalid_username_signup(self):
        """Does User.signup not create a new user with invalid username?"""
        u = User.signup(None, "test@test.com", "password", None)

        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
        
    def test_invalid_email_signup(self):
        u = User.signup('testuser', None, "password", None)

        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_password_signup(self):

        with self.assertRaises(ValueError) as context:
            User.signup('testuser', 'test@test.com', '', None)

        with self.assertRaises(ValueError) as context:
            User.signup('testuser', 'test@test.com', None, None)

######################
    def test_valid_authentication(self):
        u = User.authenticate(self.u1.username, 'password')
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.uid1)

    def test_invalid_authentication(self):
        self.assertFalse(User.authenticate('abc', 'password'))

    def test_wrong_password(self):
        self.assertFalse(User.authenticate(self.u1.username, 'abcdefgh'))


        
