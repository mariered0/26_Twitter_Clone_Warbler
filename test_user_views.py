"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
import re
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.testuser_id = 5000
        self.testuser.id = self.testuser_id

        self.u1 = User.signup('abc', 'test1@gmail.com', 'password', None)
        self.u1_id = 500
        self.u1.id = self.u1_id
        self.u2 = User.signup('efg', 'test2@gmail.com', 'password', None)
        self.u2_id = 600
        self.u2.id = self.u2_id
        self.u3 = User.signup('hij', 'test3@gmail.com', 'password', None)
        self.u4 = User.signup('klm', 'test4@gmail.com', 'password', None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_index(self):
        """Test index view."""

        with self.client as c:
            resp = c.get('/users')
            

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertIn("@hij", str(resp.data))
            self.assertIn("@klm", str(resp.data))
    
    def test_users_search(self):
        """Test user search feature."""
        
        with self.client as c:
            resp = c.get('/users?q=test')

            self.assertIn('@testuser', str(resp.data))
            
            self.assertNotIn('@abc', str(resp.data))
            self.assertNotIn('@efg', str(resp.data))


    def test_user_show(self):
        """Test user's page."""

        with self.client as c:
            resp = c.get(f'/users/{self.testuser_id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn('@testuser', str(resp.data))

    def setup_likes(self):
        """Setup likes for testing."""

        m1 = Message(text='Hey', user_id=self.testuser_id)
        m2 = Message(text='Getting hungry', user_id=self.testuser_id)
        m3 = Message(id=9000, text='nice summer day', user_id=self.u1_id)
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        l1 = Likes(user_id=self.testuser_id, message_id=9000)

        db.session.add(l1)
        db.session.commit()

    def test_user_show_with_likes(self):
        """Test the stats in the user's page."""

        self.setup_likes()
        with self.client as c:
            resp = c.get(f'/users/{self.testuser_id}')

            self.assertEqual(resp.status_code, 200)

            self.assertIn('@testuser', str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 2 messages
            self.assertIn("2", found[0].text)

            # Test for a count of 0 followers
            self.assertIn("0", found[1].text)

            # Test for a count of 0 following
            self.assertIn("0", found[2].text)

            # Test for a count of 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        """Test add_like feature."""

        m = Message(id=9000, text="Nice summer day", user_id=self.u1_id)
        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post("/users/add_like/9000", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==9000).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser_id)

    def test_remove_like(self):
        """Test unlike feature."""
        self.setup_likes()

        m = Message.query.filter(Message.text=="nice summer day").one()
        self.assertIsNotNone(m)
        self.assertNotEqual(m.user_id, self.testuser_id)

        l = Likes.query.filter(
            Likes.user_id==self.testuser_id and Likes.message_id==m.id
        ).one()

        self.assertIsNotNone(l)

        with self.client as c:
                with c.session_transaction() as sess:
                    sess[CURR_USER_KEY] = self.testuser_id

#likeing for the second time result in removing the like from the msg
                resp = c.post(f"/users/add_like/{m.id}", follow_redirects=True)
                self.assertEqual(resp.status_code, 200)

                likes = Likes.query.filter(Likes.message_id==m.id).all()
                # the like has been deleted
                self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        """Test liking by unauthenticated user."""
        self.setup_likes()

        m = Message.query.filter(Message.text=="nice summer day").one()
        self.assertIsNotNone(m)

        like_count = Likes.query.count()

        with self.client as c:

            resp = c.post(f"/users/add_like/{m.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # The number of likes has not changed since making the request
            self.assertEqual(like_count, Likes.query.count())

    def setup_followers(self):
        """Set up followers for test"""
        f1 = Follows(user_being_followed_id=self.u1_id, user_following_id=self.testuser_id)
        f2 = Follows(user_being_followed_id=self.u2_id, user_following_id=self.testuser_id)
        f3 = Follows(user_being_followed_id=self.testuser_id, user_following_id=self.u1_id)

        db.session.add_all([f1,f2,f3])
        db.session.commit()

    def test_user_show_with_follows(self):
        """Test stats # in user page."""
        self.setup_followers()

        with self.client as c:
            resp = c.get(f'/users/{self.testuser_id}')

            self.assertEqual(resp.status_code, 200)

            self.assertIn('@testuser', str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all('li', {'class': 'stat'})
            self.assertEqual(len(found), 4)

            # test for a count of 0 messages
            self.assertIn("0", found[0].text)

            # Test for a count of 2 following
            self.assertIn("2", found[1].text)

            # Test for a count of 1 follower
            self.assertIn("1", found[2].text)

            # Test for a count of 0 likes
            self.assertIn("0", found[3].text)

    def test_show_following(self):
        """Test # of following users."""

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

        resp = c.get(f'/users/{self.testuser_id}/following')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('@abc', str(resp.data))
        self.assertIn('@efg', str(resp.data))
        self.assertNotIn('@hij', str(resp.data))

    def test_show_followers(self):
        """Test # of followers"""

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

        resp = c.get(f'/users/{self.testuser_id}/followers')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('@abc', str(resp.data))
        self.assertNotIn('@efg', str(resp.data))
        self.assertNotIn('@hij', str(resp.data))


    def test_unauthorized_following_page_access(self):
        """Test following user page without authorization"""
        self.setup_followers()
        with self.client as c:
            
            resp = c.get(f'/users/{self.testuser_id}/following', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('@abc', str(resp.data))
            self.assertIn('Access unauthorized', str(resp.data))
    
    def test_unauthorized_followers_page_access(self):
        """Test user's follower page without authorization"""
        self.setup_followers()
        with self.client as c:
            
            resp = c.get(f'/users/{self.testuser_id}/followers', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('@abc', str(resp.data))
            self.assertIn('Access unauthorized', str(resp.data))






    








        


    
    





        



