#!/usr/bin/env python

# -----------------------------------------------------------------------
# CASClient.py
# Authors: Alex Halderman, Scott Karlin, Brian Kernighan, Bob Dondero
# -----------------------------------------------------------------------

from urllib.request import urlopen
from urllib.parse import quote
from re import sub, match
from flask import request, session, redirect, abort
from sys import stderr
import requests

# -----------------------------------------------------------------------


class CASClient:

    # -------------------------------------------------------------------

    # Initialize a new CASClient object so it uses the given CAS
    # server, or fed.princeton.edu if no server is given.

    def __init__(self, url="https://fed.princeton.edu/cas/"):
        self.cas_url = url

    # -------------------------------------------------------------------

    # Return the URL of the current request after stripping out the
    # "ticket" parameter added by the CAS server.

    def stripTicket(self):
        url = request.url
        if url is None:
            return "something is badly wrong"
        url = sub(r"ticket=[^&]*&?", "", url)
        url = sub(r"\?&?$|&$", "", url)
        return url

    # -------------------------------------------------------------------

    # Validate a login ticket by contacting the CAS server. If
    # valid, return the user's username; otherwise, return None.

    def validate(self, ticket):
        val_url = (
            self.cas_url
            + "validate"
            + "?service="
            + quote(self.stripTicket())
            + "&ticket="
            + quote(ticket)
        )
        r = requests.get(val_url).text.split("\n")[:-1]  # returns 2 lines
        if len(r) != 2:
            return None
        firstLine = r[0]
        secondLine = r[1]
        if not firstLine.startswith("yes"):
            return None
        return secondLine

    # -------------------------------------------------------------------

    def authenticate(self):
        # If the user's username is in the session, then the user was
        # authenticated previously.  So return the user's username.
        if "username" in session:
            if "impostor" in session and self.isAdmin():
                if session["impostor"]:
                    return session["impostor"]
            old = session.get("username")
            if old != old.strip():
                session["username"] = old.strip()
            return session.get("username")

        # If the request contains a login ticket, then try to
        # validate it.
        ticket = request.args.get("ticket")
        if ticket is not None:
            username = self.validate(ticket)
            if username is not None:
                # The user is authenticated, so store the user's
                # username in the session.
                session["username"] = username.strip()
                return session["username"]

        # The request does not contain a valid login ticket, so
        # redirect the browser to the login page to get one.
        login_url = self.cas_url + "login" + "?service=" + quote(self.stripTicket())

        abort(redirect(login_url))

    # -------------------------------------------------------------------

    # Logout the user.

    def logout(self):

        # Delete the user's username from the session.
        session.pop("username")

        # Redirect the browser to the logout page.
        logout_url = self.cas_url + "logout"
        abort(redirect(logout_url))


# -----------------------------------------------------------------------


def main():
    print("CASClient does not run standalone")


if __name__ == "__main__":
    main()
