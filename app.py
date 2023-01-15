# -----------------------------------------------------------------------
# app.py
# Authors: Caroline di Vittorio and Kasey McFadden
# -----------------------------------------------------------------------

from flask_mail import Mail, Message
from flask import Flask, request, make_response, render_template, redirect
from sys import argv
from CASClient import CASClient
from emails import *
from student import Student
from database import *
from cycle import Cycle

# from scraper import scrape
# from breakdown import Breakdown
from alert import Alert
import datetime
import os

import pustatus

from flask_login import (
    login_user,
    logout_user,
    login_required,
    LoginManager,
    current_user,
)
from userAccount import userAccount

# -----------------------------------------------------------------------


# Set LOCAL to True to bypass CAS and other authentication checks.
# Do this for local development.
# LOCAL = True
LOCAL = False

NETID = "[netid]"
if LOCAL:
    # You may set to your own NETID
    NETID = "cmdv"

# Set TESTING to True so side effects (like sending emails) don't execute.
# Do this for local development.
# TESTING = True
TESTING = False

# Set LOGIN_DISABLED to True to deactivate the flask login plugins
# e.g. @login_required no longer forces user login.
# Do this for local development.
# LOGIN_DISABLED=True
LOGIN_DISABLED = False

# -----------------------------------------------------------------------

login_manager = LoginManager()

app = Flask(__name__, template_folder="./templates")


app.config.update(
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_SUPPRESS_SEND=False,
    MAIL_PORT=os.environ.get("MAIL_PORT"),
    MAIL_SERVER=os.environ.get("MAIL_SERVER"),
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    LOGIN_DISABLED=LOGIN_DISABLED,
)

login_manager.init_app(app)

login_manager.login_view = "/"

app.secret_key = "super secret key"  # os.environ['SECRET_KEY']
cas = CASClient()
mail = Mail(app)

# ------------------------------------------------------------------------------

# returns special, undergraduates or other
def uservalidation(netid):
    special = isAdmin(netid)
    if special:
        return "special"
    else:
        return "undergraduates"


# checks that the user's role matches the page type
def checkuser(role, pageType):
    if role == pageType:
        return True
    elif role == "special":
        return True
    else:
        return False


def loginfail(isAdminPage=False):
    html = render_template("loginfail.html", isAdminPage=isAdminPage)
    response = make_response(html)
    return response


@login_manager.user_loader
def load_user(user_id):
    try:
        username = CASClient().authenticate()
        if user_id != username:
            return None
        role = uservalidation(user_id)
        return userAccount(user_id, role)
    except Exception as e:
        return loginfail()


# -----------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
# adds the student with the relevant netid to the class relevant class. If the student is assigned a study group
# where the student is the only member, sends a special email. Otherwise, send an email to the student and all
# others in the study group informing of the new student.
def _addStudentToClass(netid, class_dept, class_num):
    alert_response = addStudentToClass(netid, class_dept, class_num)
    if alert_response.getType() == "failure":
        return -1

    groupid = alert_response.getMessage()

    endorsement_status = getClassEndorsement(class_dept, class_num)

    if endorsement_status == 0:
        return groupid

    if endorsement_status == 1:
        if not TESTING:
            emails = waitingApprovalEmail(class_dept, class_num, netid)
            mail.send(emails[0])
            mail.send(emails[1])
        return groupid

    students_in_group = getStudentsInGroup(groupid)
    if len(students_in_group) <= 1:
        if not TESTING:
            mail.send(newGroupWelcomeEmail(netid, groupid))
    else:
        if not TESTING:
            mail.send(newStudentWelcomeEmail(netid, students_in_group, groupid))

    return groupid


def _switchStudentInClass(netid, class_dept, class_num):
    switch_alert = switchGroup(netid, class_dept, class_num)
    if switch_alert.getType() == "failure":
        return -1

    groupid = switch_alert.getMessage()
    endorsement_status = getClassEndorsement(class_dept, class_num)

    if endorsement_status == 0:
        return groupid

    if endorsement_status == 1:
        if not TESTING:
            emails = waitingApprovalEmail(class_dept, class_num, netid)
            mail.send(emails[0])
            mail.send(emails[1])
        return groupid

    students_in_group = getStudentsInGroup(groupid)
    if len(students_in_group) <= 1:
        if not TESTING:
            mail.send(newGroupWelcomeEmail(netid, groupid))
    else:
        if not TESTING:
            mail.send(newStudentWelcomeEmail(netid, students_in_group, groupid))

    return groupid


# ------------------------------------------------------------------------------
# STUDENT JOIN CLASS PORTAL
# ------------------------------------------------------------------------------
@app.route("/")
@app.route("/home")
def home():
    netid = NETID
    isFirstLogin = True
    if not LOCAL:
        netid = cas.authenticate()
        # determine whether this is the user's first login
        isFirstLogin = firstLogin(netid)
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)

        if not check:
            return loginfail()
        else:
            useraccount = userAccount(netid, role)
            login_user(useraccount)

        if isFirstLogin:
            createNewStudent(netid)
            if not TESTING:
                mail.send(welcomeEmail(netid))

    html = render_template(
        "index.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        isFirstLogin=isFirstLogin,
    )

    response = make_response(html)
    return response


@app.route("/search", methods=["GET"])
@login_required
def searchResults():
    dept = request.args.get("dept")
    coursenum = request.args.get("coursenum")

    if len(dept) + len(coursenum) < 1:
        html = '<div class="row" style="background-color:bisque; margin:0; padding:0; height:100%">\
                    <div class="row" style="width:100%;">\
                        <div class="container p-5"><center><h1>We\'re so glad you\'re here!</h1></center></div>\
                    </div>'
        html += '<div class="row" style="width: 100%">\
                    <div class="col-4">\
                        <div style = "border:2px; border-style:solid; border-color:grey; border-radius: 1vw;padding: 1em; margin: 1em">\
                            <center><h3>Step 1</h3><br>Start by searching above for the classes you are taking. Find your classes!<br> </center>\
                        </div>\
                    </div>\
                    <div class="col-4">\
                        <div style = "border:2px; border-style:solid; border-color:grey; border-radius: 1vw;padding: 1em; margin: 1em">\
                            <center><h3>Step 2</h3><br>Click on the "Join" button to join a group. You\'ll be instantly placed into a group\
                                and we will send you an email with your partnering details.\
                            </center>\
                        </div>\
                    </div>\
                    <div class="col-4">\
                        <div style = "border:2px; border-style:solid; border-color:grey; border-radius: 1vw;padding: 1em; margin: 1em">\
                            <center><h3>Step 3</h3><br>Find a time that suits your group, and start studying together. Be sure to follow\
                                course policies on collaboration!<br> \
                            </center>\
                        </div>\
                    </div>\
                </div><div class="row" style="height: 20vh"><br><br><br></div>\
                </div>'
        return make_response(html)

    courses = search(dept, coursenum)

    html = (
        '<table class="table table-striped justify-content-between"> '
        "<thead> "
        "<tr> "
        '<th align = "left">Dept</th> '
        '<th align = "left">Num</th> '
        + '<th align = "left">Title</th> '
        + '<th align = "right">  </th> '
        + '<th align = "right">  </th> '
        + "</tr>"
        + "</thead>"
        "<tbody> "
    )
    for course in courses:
        numgroups = numberGroupsInClass(course.getDept(), course.getNum())
        if not LOCAL:
            netid = current_user.id
        else:
            netid = "cmdv"
        alreadyJoined = getJoinedClasses(netid)
        html += (
            "<tr>\n"
            + "<td> "
            + course.getDept()
            + " </td>\n"
            + "<td> "
            + course.getNum()
            + " </td>\n"
            + "<td> "
            + course.getTitle()
            + " </td>\n"
        )

        if numgroups > 0:
            html += (
                "<td> "
                + '<span class="badge badge-primary badge-pill" style="float:right">'
                + str(numgroups)
                + " group"
            )
            if numgroups > 1:
                html += "s"
            html += "</span>" + " </td>\n"
        else:
            html += "<td>  </td>"

        if [course.getDept(), course.getNum()] in alreadyJoined:
            html += (
                '<td> <a href="mygroups" style="color:black">Group #'
                + str(
                    getGroupOfStudentInClass(netid, course.getDept(), course.getNum())
                )
                + "</a> </td>\n</tr>\n"
            )
        elif course.isEndorsed() == 0:
            html += "<td>Not Approved</td>"
        else:
            html += (
                "<td> "
                + '<button type="button" class="joinButton btn btn-link" id="joinButton" style="padding: 0px; color:black; float:center"'
                + 'data-toggle="modal" data-target="#joinModal" data-dept="'
                + str(course.getDept())
                + '" data-num="'
                + str(course.getNum())
                + '" data-notes="'
                + str(course.getNotes())
                + '"<h6>Join</h6> </button>'
                + " </td>\n</tr>\n"
            )

    html += "</tbody></table>"
    response = make_response(html)
    return response


@app.route("/joinClass", methods=["GET"])
@login_required
def joinStudentToClass():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail()

    dept = request.args.get("dept")
    num = request.args.get("classnum")

    print("info passed along")
    print(dept)
    print(num)

    # if isStudentInClass(netid, dept, coursenum):
    #     html = '<br><div class="alert alert-danger" role="alert">' + \
    #            'You\'ve already joined a group for this class!</div>'
    #     response = make_response(html)
    #     return response

    groupId = _addStudentToClass(netid, dept, num)

    # html = ''
    # html += '<br>'
    # html += '<div class="alert alert-success" role="alert">'
    # html += '<p>Successfully joined group! <br>'
    # html += 'View your group in the "My Groups" tab.</p>'
    # html += '</div>'

    return redirect("home")


# -----------------------------------------------------------------------
# ADMIN BREAKDOWN AND GENERAL SITE ADMIN
# -----------------------------------------------------------------------
# About: include some info about the site
@app.route("/admin")
@login_required
def admin():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    html = render_template(
        "admin.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        curr_admin=getAdmin(),
        curr_faculty=getFaculty(),
        breakdown=getAdminBreakdown(),
        cycle=getCycleInfo(),
        alert=["None", "None", "None", "None"],
    )
    response = make_response(html)
    return response


@app.route("/start_new_semester", methods=["POST"])
@login_required
def start_new_semester():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    # sem = request.form.get('sem')
    # year = request.form.get('year')

    # print(sem)
    # print(year)

    # calculate term number - starting point:
    # 1222 = Fall 2021,
    # term = 1222 + 3 * (int(year) - 2022)
    # if sem =="fall":
    #     term += 3
    # elif sem == "spring":
    #     term += 1
    # elif sem == "summer":
    #     term += 2

    reset_classes(netid)

    return redirect("admin")


@app.route("/edit_admin", methods=["GET", "POST"])
@login_required
def edit_admin():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    admin_user = request.args.get("netid")
    print("admin user " + str(admin_user))
    action_type = request.args.get("action")
    print("action_type" + str(action_type))

    alert = []
    if action_type == "add_admin":
        email_list = request.args.get("email_list") == "on"
        alert.append(addAdmin(admin_user, email_list))
    else:
        alert.append("None")
    if action_type == "remove_admin":
        alert.append(deleteAdmin(admin_user))
    else:
        alert.append("None")
    if action_type == "add_faculty":
        alert.append(addFaculty(admin_user))
    else:
        alert.append("None")
    if action_type == "remove_faculty":
        alert.append(deleteFaculty(admin_user))
    else:
        alert.append("None")

    html = render_template(
        "admin.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        curr_admin=getAdmin(),
        curr_faculty=getFaculty(),
        breakdown=getAdminBreakdown(),
        cycle=getCycleInfo(),
        alert=alert,
    )
    response = make_response(html)
    return response


@app.route("/get_email_templates")
@login_required
def get_email_templates():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    return {"res": getEmailTemplates()}


@app.route("/update_email_template", methods=["POST"])
@login_required
def update_email_template():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    type_ = request.form.get("type")
    subject = request.form.get("subject")
    body = request.form.get("body")

    if not (type_ and subject and body):
        return redirect("admin")

    print(f"Updating email type: {type_}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")

    updateEmailTemplate(type_, subject, body)

    return redirect("admin")


# ------------------------------------------------------------------------------
# EDIT COURSE INFORMATION AND MANUAL GROUP INTERVENTION
# ------------------------------------------------------------------------------
@app.route("/admin_courses")
@login_required
def admin_courses():
    print("in admin courses")
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)
        useraccount = userAccount(netid, role)
        login_user(useraccount)

    groups_by_dept, dept_course_data = getMetrics()

    html = render_template('admin_courses_new.html',
                           netid=netid,
                           isAdmin=isAdmin(netid),
                           groups_by_dept=groups_by_dept,
                           dept_course_data=dept_course_data,
                           )
    response = make_response(html)
    return response


@app.route("/searchAdmin", methods=["GET"])
@login_required
def searchAdminResults():
    dept = request.args.get("dept")
    coursenum = request.args.get("coursenum")

    courses = search(dept, coursenum)

    html = (
        '<table class="table table-striped"> '
        "<thead> "
        "<tr> "
        '<th align = "left">Dept</th> '
        '<th align = "left">Num</th> '
        + '<th align = "left">Title</th> '
        + '<th align = "right">  </th> '
        + "</tr>"
        + "</thead>"
        "<tbody> "
    )
    for course in courses:

        html_form = (
            '<form action="edit_course" method="get">\
            <input type="hidden" name="dept" value='
            + course.getDept()
            + '>\
            <input type="hidden" name="classnum" value='
            + course.getNum()
            + '>\
            <input type="submit" class="btn" value="Edit Course Information">\
        </form>'
        )

        html += (
            "<tr>\n"
            + "<td> "
            + course.getDept()
            + " </td>\n"
            + "<td> "
            + course.getNum()
            + " </td>\n"
            + "<td> "
            + course.getTitle()
            + " </td>\n"
        )
        html += "<td> " + html_form + "</td>\n"

    html += "</tbody></table>"
    response = make_response(html)
    return response


@app.route("/edit_course", methods=["GET"])
@login_required
def edit_course():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    dept = request.args.get("dept")
    classnum = request.args.get("classnum")

    course = getCourse(dept, classnum)
    group_overview = getGroupsInClass(dept, classnum)
    groups = []
    for g in group_overview:
        groups.append([g, getStudentsInGroup(g.getGroupId())])

    html = render_template(
        "admin_edit_course.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        course=course,
        groups=groups,
    )
    response = make_response(html)
    return response


@app.route("/admin_override", methods=["POST"])
@login_required
def admin_override():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    override_type = request.form.get("override_type")
    override_netid = request.form.get("override_netid")
    dept = request.form.get("dept")
    classnum = request.form.get("classnum")

    print("Data that is passed yay!")
    print(override_netid)
    print(dept)
    print(classnum)

    if override_type == "remove":
        groupid = request.form.get("groupid")
        removeStudentFromGroup(override_netid, groupid, dept, classnum)

    elif override_type == "move":
        groupid = getGroupOfStudentInClass(override_netid, dept, classnum)
        new_groupid = request.form.get("new_groupid")
        removeStudentFromGroup(override_netid, groupid, dept, classnum)
        addStudentToGroup(override_netid, new_groupid)

        endorsement_status = getClassEndorsement(dept, classnum)

        if endorsement_status == 1:
            if not TESTING:
                emails = waitingApprovalEmail(dept, classnum, override_netid)
                mail.send(emails[0])
                mail.send(emails[1])

        students_in_group = getStudentsInGroup(new_groupid)
        if len(students_in_group) <= 1:
            if not TESTING:
                mail.send(newGroupWelcomeEmail(override_netid, new_groupid))
        else:
            if not TESTING:
                mail.send(
                    newStudentWelcomeEmail(
                        override_netid, students_in_group, new_groupid
                    )
                )

    elif override_type == "add":
        new_groupid = request.form.get("new_groupid")
        removeStudentFromGroup(override_netid, new_groupid, dept, classnum)
        addStudentToGroup(override_netid, new_groupid)

        endorsement_status = getClassEndorsement(dept, classnum)

        if endorsement_status == 1:
            if not TESTING:
                emails = waitingApprovalEmail(dept, classnum, override_netid)
                mail.send(emails[0])
                mail.send(emails[1])

        students_in_group = getStudentsInGroup(new_groupid)
        if len(students_in_group) <= 1:
            if not TESTING:
                mail.send(newGroupWelcomeEmail(override_netid, new_groupid))
        else:
            if not TESTING:
                mail.send(
                    newStudentWelcomeEmail(
                        override_netid, students_in_group, new_groupid
                    )
                )

    course = getCourse(dept, classnum)
    group_overview = getGroupsInClass(dept, classnum)
    groups = []
    for g in group_overview:
        groups.append([g, getStudentsInGroup(g.getGroupId())])

    html = render_template(
        "admin_edit_course.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        course=course,
        groups=groups,
    )
    response = make_response(html)
    return response


@app.route("/submit_course_edits")
@login_required
def submit_course_edits():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    dept = request.args.get("dept")
    classnum = request.args.get("classnum")
    status = request.args.get("status")
    if status == "Pending":
        endorse_status = 1
    elif status == "Denied":
        endorse_status = 0
    else:
        endorse_status = 2
    notes = request.args.get("notes")

    action = approveCourse(dept, classnum, endorse_status, notes)
    if action is not None:
        if action[0] == 0:
            if not TESTING:
                mail.send(courseDeniedEmail(action[1], dept, classnum))
        if action[0] == 2:
            if not TESTING:
                emails = courseApprovedEmail(action[1], dept, classnum)
                for email in emails:
                    mail.send(email)

    html = render_template(
        "admin_courses.html",
        netid=netid,
        isAdmin=isAdmin(netid),
    )
    response = make_response(html)
    return response


@app.route("/admin_students")
@login_required
def admin_students():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)
        useraccount = userAccount(netid, role)
        login_user(useraccount)

    html = render_template(
        "admin_students.html",
        netid=netid,
        isAdmin=isAdmin(netid),
    )
    response = make_response(html)
    return response


@app.route("/searchAdminStudents", methods=["GET"])
@login_required
def searchAdminStudentsResults():
    netid = request.args.get("netid")

    students = searchStudents(netid)

    html = (
        '<table class="table table-striped"> '
        "<thead> "
        "<tr> "
        '<th align = "left">Netid</th> '
        '<th align = "left">Name</th> '
        '<th align = "right">  </th> ' + "</tr>" + "</thead>"
        "<tbody> "
    )
    for student in students:

        html_form = (
            '<form action="view_student" method="get">\
            <input type="hidden" name="netid" value='
            + student.getNetid()
            + '>\
            <input type="submit" class="btn" value="View Student Profile">\
        </form>'
        )

        html += (
            "<tr>\n"
            + "<td> "
            + student.getNetid()
            + " </td>\n"
            + "<td> "
            + student.getFirstName()
            + " "
            + student.getLastName()
            + " </td>\n"
        )
        html += "<td> " + html_form + "</td>\n"

    html += "</tbody></table>"
    response = make_response(html)
    return response


@app.route("/view_student", methods=["GET"])
@login_required
def view_student():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "special"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail(True)

    netid = request.args.get("netid")
    student = getStudentInformation(netid)
    courses = getJoinedClasses(netid)
    courses_long = []
    for course in courses:
        title = getCourseTitle(course[0], course[1])
        groupid = getGroupOfStudentInClass(netid, course[0], course[1])
        courses_long.append([course[0], course[1], title, groupid])
    # group_overview = getGroupsInClass(dept, classnum)
    # groups = []
    # for g in group_overview:
    #     groups.append([g, getStudentsInGroup(g.getGroupId())])

    html = render_template(
        "admin_view_student.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        student=student,
        courses=courses_long,
    )
    response = make_response(html)
    return response


# ------------------------------------------------------------------------------
# MYGROUPS
# ------------------------------------------------------------------------------
# -----------------------------------------------------------------------
@app.route("/mygroups")
@login_required
def myGroups(alert="None"):
    netid = NETID

    if not LOCAL:
        netid = cas.authenticate()
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail()

    myGroups = []

    if not TESTING:
        groups = getPublicJoinedGroups(netid)
    else:
        groups = getJoinedGroups(netid)

    for groupId in groups:
        group = {}
        info = getGroupInformation(groupId)
        students = getStudentsInGroup(groupId)
        group["groupId"] = groupId
        group["dept"] = info.getClassDept()
        group["coursenum"] = info.getClassNum()
        group["title"] = group["dept"] + " " + group["coursenum"]
        group["students"] = students
        myGroups.append(group)

    html = render_template(
        "mygroups.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        myGroups=myGroups,
        std_info=getStudentInformation(netid),
        contact_alert="None",
    )

    response = make_response(html)
    return response


# -----------------------------------------------------------------------
# Get My Group Info: display the info for a selected group that I joined
@app.route("/getMyGroupInfo", methods=["GET"])
@login_required
def getMyGroupInfo():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate().strip()
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail()

    groupId = request.args.get("groupId")
    group = getGroupInformation(groupId)
    students = getStudentsInGroup(groupId)
    dept = group.getClassDept()
    coursenum = group.getClassNum()

    html = '<div class="container">'
    html += (
        '<div class="row">\
                <div class="col-6">\
                    <h1>'
        + str(dept)
        + " "
        + str(coursenum)
        + '</h1>\
                </div>\
                <div class="col-6">\
                    <button type="button" class="class-leave-btn btn btn-link" id="changeGroup" style="color:grey; align-text:right" '
        + 'groupId="'
        + groupId
        + '" dept="'
        + dept
        + '" coursenum="'
        + coursenum
        + '" onclick="changeGroup(this)"><h6>'
        + "Switch Groups"
        + '</h6></button><br>\
                    <button type="button" class="class-leave-btn btn btn-link " id="leaveGroup" style="color:grey; align-text:right" '
        + 'groupId="'
        + groupId
        + '" dept="'
        + dept
        + '" coursenum="'
        + coursenum
        + '" onclick="leaveGroup(this)"><h6>'
        + "Leave Group"
        + "</h6></button>\
                </div>\
            </div>"
    )
    # html += '<h1>' + str(dept) + ' ' + str(coursenum) + '</h1>'

    html += '<div class="row" style="text-align:center">'
    if students == [netid]:
        html += (
            "<p>"
            + "<br><br>You're the first member of your group. Don't worry, you'll be matched soon, and we will\
        let you know ASAP!"
            + "</p>"
        )
    else:
        html += (
            '<table class="table">'
            + '<thead class="thead-light">'
            + '<tr><th scope="col" colspan="4">Partners</tr>'
            + "</thead>"
            + '<thead class="thead-dark">'
            + "<tr>"
            + '<th scope="col">First</th>'
            + '<th scope="col">Last</th>'
            + '<th scope="col">netid</th>'
            + '<th scope="col">Phone</th>'
            + "</tr>"
            + "</thead>"
            + "<tbody>"
        )

        for studentNetid in students:
            if str(studentNetid) != str(netid):
                student = getStudentInformation(studentNetid)
                print("studentInfo", student)
                if student is not None:
                    html += (
                        "<tr>"
                        + "<td>"
                        + str(student.getFirstName())
                        + "</td>"
                        + "<td>"
                        + str(student.getLastName())
                        + "</td>"
                        + "<td>"
                        + '<a href="mailto:'
                        + str(studentNetid)
                        + '@princeton.edu" target="_blank">'
                        + str(studentNetid)
                        + "</a>"
                        + "</td>"
                        + "<td>"
                        + str(student.getPhone())
                        + "</td>"
                        + "</tr>"
                    )

        html += "</tbody>" + "</table></div></div>"

    # html += '<br><br>'

    # html += '<button type="button" class="class-leave-btn btn btn-warning btn-lg" id="changeGroup" ' \
    #         + 'groupId="' + groupId + '" dept="' + dept + '" coursenum="' + coursenum \
    #         + '" onclick="changeGroup(this)"><h4>' + 'Switch Groups' + '</h4></button>'

    # html += '<br><br>'

    # html += '<button type="button" class="class-leave-btn btn btn-danger btn-lg" id="leaveGroup" ' \
    #         + 'groupId="' + groupId + '" dept="' + dept + '" coursenum="' + coursenum \
    #         + '" onclick="leaveGroup(this)"><h4>' + 'Leave Group' + '</h4></button>'

    response = make_response(html)
    return response


# -----------------------------------------------------------------------
# Leave Group: leave a group
@app.route("/leaveGroup", methods=["GET"])
@login_required
def leaveGroup():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail()

    groupId = request.args.get("groupId")
    dept = request.args.get("dept")
    coursenum = request.args.get("coursenum")

    removeStudentFromGroup(netid, groupId, dept, coursenum)

    html = ""
    html += "<br>"
    html += '<div class="alert alert-success" role="alert">'
    html += "You have left the group."

    response = make_response(html)
    return response


# -----------------------------------------------------------------------
# Change Group: get a different group
@app.route("/changeGroup", methods=["GET"])
@login_required
def changeGroup():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail()

    groupId = request.args.get("groupId")
    dept = request.args.get("dept")
    coursenum = request.args.get("coursenum")

    _switchStudentInClass(netid, dept, coursenum)

    html = ""
    html += "<br>"
    html += '<div class="alert alert-success" role="alert">'
    html += "You have been assigned a new group."

    response = make_response(html)
    return response


@app.route("/editContact", methods=["POST"])
@login_required
def edit_contact():
    print("here")
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        pageType = "undergraduates"
        role = uservalidation(netid)
        check = checkuser(role, pageType)
        if not check:
            return loginfail()

    fname = request.form.get("fname-input")
    lname = request.form.get("lname-input")
    phone = request.form.get("phone-input")

    contact_alert = updateStudent(Student([netid, fname, lname, phone, None, None]))

    myGroups = []

    if not TESTING:
        groups = getPublicJoinedGroups(netid)
    else:
        groups = getJoinedGroups(netid)

    for groupId in groups:
        group = {}
        info = getGroupInformation(groupId)
        students = getStudentsInGroup(groupId)
        group["groupId"] = groupId
        group["dept"] = info.getClassDept()
        group["coursenum"] = info.getClassNum()
        group["title"] = group["dept"] + " " + group["coursenum"]
        group["students"] = students
        myGroups.append(group)

    html = render_template(
        "mygroups.html",
        netid=netid,
        isAdmin=isAdmin(netid),
        myGroups=myGroups,
        std_info=getStudentInformation(netid),
        contact_alert=contact_alert,
    )

    response = make_response(html)
    return response


# ------------------------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------------------------
@app.route("/logout")
def logout():
    netid = NETID
    if not LOCAL:
        netid = cas.authenticate()
        cas.logout()


# ------------------------------------------------------------------------------
# TESTING
# ------------------------------------------------------------------------------


# -----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(argv[1]), debug=True)
