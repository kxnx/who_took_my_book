from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail

import cgi
import logging

from eventregistry import *
###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"

class IllegalStateTransition(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class DuplicateBook(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class BookWithoutTitle(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class WtmbException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
###################################################################
class AppUser(db.Model):
    googleUser = db.UserProperty()
    wtmb_nickname = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add = "true")
    last_login_date = db.DateTimeProperty(auto_now = "true")

    def is_outsider(self):
        return not self.googleUser

    @staticmethod
    def create_outsider(name):
        if not name or name.strip() == "":
            raise ValueError("Name cannot be empty")
        if AppUser.gql('WHERE googleUser = :1 and wtmb_nickname= :2', None, name).get():
            raise ValueError("This name is already taken")
        new_user = AppUser(wtmb_nickname = name)
        new_user.put()
        return new_user

    @classmethod
    def on_new_user_registration(cls, new_user):
        mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [new_user.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] Welcome',
                     body = "Thanks for choosing to use http://whotookmybook.appspot.com")

    @staticmethod
    def getAppUserFor(aGoogleUser):
        appuser = AppUser.gql('WHERE googleUser = :1', aGoogleUser).get()
        if appuser is None:
            current_user = users.get_current_user()
            appuser = AppUser(googleUser = current_user, wtmb_nickname = current_user.nickname())
            appuser.put()
            NewUserRegistered(appuser).fire()
        return appuser

    def display_name(self):
        return self.wtmb_nickname if self.wtmb_nickname else self.googleUser.nickname()

    def email(self):
        return self.googleUser.email() if self.googleUser else "whotookmybook+unregistered_user_" + self.wtmb_nickname + "@gmail.com"

    def change_nickname(self, new_nick):
        self.wtmb_nickname = new_nick
        self.put()

    def update_last_login(self):
        self.put()

    def to_hash(self):
        return {
                                 "nickname": self.display_name(),
                                 "email": self.email(),
                                 "last_login": self.last_login_date.toordinal() #isoformat() + 'Z'
                                        }

    @staticmethod
    def me():
        return AppUser.gql('WHERE googleUser = :1', users.get_current_user()).get()

    @staticmethod
    def others():
        return AppUser.gql('WHERE googleUser != :1', users.get_current_user())

NewUserRegistered().subscribe(AppUser.on_new_user_registration)
###################################################################        
class Book(db.Model):
    author = db.StringProperty()
    owner = db.ReferenceProperty(AppUser, collection_name = "books_owned")
    title = db.StringProperty()
    borrower = db.ReferenceProperty(AppUser, collection_name = "books_borrowed", required = False)
    asin = db.StringProperty()
    is_technical = db.BooleanProperty()
    dewey = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add = "true")

    def __init__(self, parent = None, key_name = None, **kw):
        super(Book, self).__init__(parent, key_name, **kw)
        if self.title.strip() == "":
            raise BookWithoutTitle("Title required")
        if self.author.strip() == "":
            self.author = "unknown"

    def to_hash(self):
        return {
                                        "title": cgi.escape(self.title),
                                        "author":cgi.escape(self.author),
                                        "is_tech": self.is_technical,
                                        "dewey": self.dewey,
                                        "borrowed_by": cgi.escape(self.borrower_name()),
                                        "owner": cgi.escape(self.owner.display_name()),
                                        "key": str(self.key()),
                                        "asin":self.asin,
                                        "added_on": self.created_date.toordinal()
                                        }

    def summary(self):
        return self.title + ' by ' + self.author

    def borrower_name(self):
        try:
            return self.borrower.display_name()
        except AttributeError:
            return str(None)

    def is_available(self):
        return None == self.borrower

    def is_lent(self):
        return None != self.borrower

    def belongs_to_someone_else(self):
        return users.get_current_user() != self.owner.googleUser

    def belongs_to_me(self):
        return users.get_current_user() == self.owner.googleUser

    def borrowed_by_me(self):
        if self.borrower:
            return users.get_current_user() == self.borrower.googleUser
        return False

    def __change_borrower(self, new_borrower):
        self.borrower = new_borrower

    def __duplicate(self):
        return bool(db.GqlQuery("SELECT __key__ from Book WHERE owner = :1 and title =:2 and author = :3", AppUser.me().key(), self.title, self.author).get())

    def create(self):
        if self.__duplicate():
            raise DuplicateBook("Add failed: You (" + AppUser.me().display_name() + ") already have added '" + self.title + "'");
        self.put()
        NewBookAdded(self).fire()
        return self

    def return_to_owner(self):
        if self.borrowed_by_me() or self.belongs_to_me():
            self.__change_borrower(None)
            self.put()
            BookReturned({'book':self, 'returner': AppUser.me()}).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to return" + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to return")

    def obliterate(self):
        if self.belongs_to_me():
            self.delete()
            BookDeleted(self).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to delete " + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to delete")

    def borrow(self):
        if self.belongs_to_someone_else() and self.is_available():
            self.__change_borrower(AppUser.me())
            self.put()
            BookBorrowed(self).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to borrow " + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to borrow")

    def lend_to(self, appuser):
        if self.belongs_to_me():
            if not self.is_available():
                self.return_to_owner()
            self.__change_borrower(appuser)
            self.put()
            BookLent(self).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to lend " + self.title + " owned by " + self.owner.display_name() + " to " + appuser.display_name())
            raise IllegalStateTransition("illegal attempt to lend")

    def remind(self):
        if self.belongs_to_me() and self.is_lent():
            mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [self.owner.email(), self.borrower.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + self.title,
                     body = "Hi " + self.borrower.display_name() + "\n" \
                        + self.owner.display_name() + " would like to gently remind you to return '" + self.title + "' if you have finished with it. ")
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to remind about " + self.title + " owned by " + self.owner.display_name())
            raise WtmbException("illegal attempt to remind")

    @staticmethod
    def owned_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE owner = :1 LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def borrowed_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE borrower = :1 LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def new_books():
      from datetime import date, timedelta
      last_week = date.today() - timedelta(days = 7)
      return db.GqlQuery("SELECT __key__ from Book WHERE created_date > :1", last_week).fetch(1000)

    @staticmethod
    def on_return(info):
            returner = info['returner']
            book = info['book']
            mail.send_mail(
                         sender = WTMB_SENDER,
                         to = [returner.email(), book.owner.email()],
                         cc = WTMB_SENDER,
                         subject = '[whotookmybook] ' + book.title,
                         body = (returner.display_name() + \
                                 (" has returned this book to " + book.owner.display_name()) if (returner != book.owner) else \
                                 returner.display_name() + " has asserted possession of this book"))
    @staticmethod
    def on_borrow(book):
            mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [book.owner.email(), book.borrower.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + book.title,
                     body = book.borrower.display_name() + " has requested or borrowed this book from " + book.owner.display_name())

    @staticmethod
    def on_lent(book):
        mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [book.owner.email(), book.borrower.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + book.title,
                     body = book.owner.display_name() + " has lent this book to " + book.borrower.display_name())

    @staticmethod
    def on_add(book):
        pass

    @staticmethod
    def on_delete(book):
        pass

BookReturned().subscribe(Book.on_return)
BookLent().subscribe(Book.on_lent)
NewBookAdded().subscribe(Book.on_add)
BookDeleted().subscribe(Book.on_delete)
BookBorrowed().subscribe(Book.on_borrow)
###################################################################
