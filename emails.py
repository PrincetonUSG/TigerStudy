# -----------------------------------------------------------------------
# emails.py
# Author: Caroline di Vittorio
# -----------------------------------------------------------------------
from flask_mail import Message
from database import *


TIGERSTUDY_EMAIL = "tiger-study@princeton.edu"

# sends email to welcome new student to a new group when they are the first
# student in that group
def newGroupWelcomeEmail(netid, groupid):
    subject, body = fetchEmailTemplate("New Group Welcome Email")

    student_info = getStudentInformation(netid)
    first_name = (
        netid if student_info.getFirstName() == "" else student_info.getFirstName()
    )
    course_name = getCourseName(groupid)

    subject = subject.replace("$COURSE$", course_name)
    body = body.replace("$RECIPIENT$", str(first_name)).replace("$COURSE$", course_name)

    msg = Message(
        subject=subject,
        body=body,
        sender=TIGERSTUDY_EMAIL,
        recipients=[netid + "@princeton.edu"],
    )

    return msg


def courseDeniedEmail(netids, dept, num):
    subject, body = fetchEmailTemplate("Course Denied Email")

    emails = []
    for netid in netids:
        emails.append(str(netid) + "@princeton.edu")

    subject = subject.replace("$COURSE$", str(dept) + str(num))

    msg = Message(
        subject=subject,
        body=body,
        sender=TIGERSTUDY_EMAIL,
        recipients=emails,
    )

    return msg


def courseApprovedEmail(groups, dept, num):
    subject, body = fetchEmailTemplate("Course Approved Email")

    msgs = []
    for students in groups:
        contact_summary = ""
        email = []
        for std in students:
            s = getStudentInformation(std)
            email.append(s.getNetid() + "@princeton.edu")
            if s.getFirstName() != "":
                contact_summary += (
                    str(s.getFirstName()) + " " + str(s.getLastName()) + ": "
                )
            contact_summary += str(s.getNetid()) + "@princeton.edu\n"

        msg = Message(
            subject=subject.replace("$COURSE$", str(dept) + str(num)),
            body=body.replace("$COURSE$", str(dept) + str(num)).replace(
                "$CONTACT_INFO$", contact_summary
            ),
            sender=TIGERSTUDY_EMAIL,
            recipients=email,
        )

        msgs.append(msg)

    return msgs


# -----------------------------------------------------------------------
# sends email welcome a new student to an already existing study group
def newStudentWelcomeEmail(netid, students, groupid):
    subject, body = fetchEmailTemplate("New Student Welcome Email")

    student_info = getStudentInformation(students[0])
    if student_info.getFirstName() == "":
        student_name = student_info.getNetid()
    else:
        student_name = (
            str(student_info.getFirstName()) + " " + str(student_info.getLastName())
        )
    netid = student_info.getNetid()

    course_name = getCourseName(groupid)

    email = [netid + "@princeton.edu"]
    contact_summary = ""
    for std in students:
        s = getStudentInformation(std)
        email.append(s.getNetid() + "@princeton.edu")
        if s.getFirstName() != "":
            contact_summary += str(s.getFirstName()) + " " + str(s.getLastName()) + ": "
        contact_summary += str(s.getNetid()) + "@princeton.edu\n"

    if student_info.getFirstName() == "":
        name_msg = "A new student"
    else:
        name_msg = (
            str(student_info.getFirstName()) + " " + str(student_info.getLastName())
        )

    subject = subject.replace("$COURSE$", course_name).replace("$JOINEE$", name_msg)
    body = (
        body.replace("$COURSE$", course_name)
        .replace("$JOINEE$", student_name)
        .replace("$CONTACT_INFO$", contact_summary)
    )

    msg = Message(
        subject=subject,
        body=body,
        sender=TIGERSTUDY_EMAIL,
        recipients=email,
    )

    return msg


# -----------------------------------------------------------------------
# sends welcome email for first login of new student
def welcomeEmail(netid):
    subject, body = fetchEmailTemplate("First Login Welcome Email")

    email = [str(netid) + "@princeton.edu"]
    msg = Message(subject=subject, body=body, sender=TIGERSTUDY_EMAIL, recipients=email)

    return msg


def waitingApprovalEmail(dept, num, netid):
    subject, body = fetchEmailTemplate("Waiting Approval Email")

    subject = subject.replace("$COURSE$", str(dept) + str(num))

    email = [str(netid) + "@princeton.edu"]
    msg = Message(
        subject=subject,
        body=body,
        sender=TIGERSTUDY_EMAIL,
        recipients=email,
    )

    # TODO: replace this with toggles in the admin interface
    email_admins = [
        "gawonj@princeton.edu",
        "iokkinga@princeton.edu",
    ]
    msg_admins = Message(
        "Someone has requested to join TigerStudy for " + str(dept) + str(num),
        sender=TIGERSTUDY_EMAIL,
        recipients=email_admins,
    )
    msg_admins.body = (
        str(netid)
        + " has requested to join "
        + str(dept)
        + str(num)
        + " on TigerStudy."
    )

    return [msg, msg_admins]


def fetchEmailTemplate(type_):
    conn = db.connect()
    stmt = emails.select().where(emails.c.type == type_)
    result = conn.execute(stmt)
    conn.close()
    template = list(result)[0]
    _, subject, body = template
    return subject, body


def getCourseName(groupid):
    group_information = getGroupInformation(groupid)
    return group_information.getClassDept() + group_information.getClassNum()


if __name__ == "__main__":
    # print(fetchEmailTemplate("Waiting Approval Email"))
    # print(newGroupWelcomeEmail("tl5559", 581))
    # print(courseDeniedEmail([], "ECO", 100))
    # print(courseApprovedEmail([["ntyp"]], "ECO", 100))
    # print(newStudentWelcomeEmail("tl5559", ["tl5559", "ntyp"], 581))
    print(welcomeEmail("ntyp"))
