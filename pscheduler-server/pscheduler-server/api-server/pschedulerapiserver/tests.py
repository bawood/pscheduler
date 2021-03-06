#
# Test-Related Pages
#

import pscheduler

from pschedulerapiserver import application

from flask import request

from .dbcursor import dbcursor_query
from .json import *
from .response import *

#
# Tests
#

# All tests
@application.route("/tests", methods=['GET'])
def tests():
    return json_query("SELECT json FROM test"
                      " WHERE available ORDER BY name", [])


# Test <name>
@application.route("/tests/<name>", methods=['GET'])
def tests_name(name):
    return json_query("SELECT json FROM test"
                      " WHERE available AND name = %s",
                      [name], single=True)


# Derive a spec from command line arguments in 'arg'
@application.route("/tests/<name>/spec", methods=['GET'])
def tests_name_spec(name):

    try:
        cursor = dbcursor_query("SELECT EXISTS (SELECT * FROM test"
                                "  WHERE available AND name = %s)",
                                [ name ])
    except Exception as ex:
        return error(str(ex))

    exists = cursor.fetchone()[0]
    cursor.close()
    if not exists:
        return not_found()

    try:
        args = arg_json('args')
    except ValueError as ex:
        return bad_request("JSON passed to 'args': %s " % (str(ex)))

    status, stdout, stderr = pscheduler.run_program(
        [ 'pscheduler', 'internal', 'invoke', 'test', name, 'cli-to-spec' ],
        stdin = pscheduler.json_dump(args),
        timeout=5
        )

    if status != 0:
        return bad_request(stderr)

    # The extra parse here makes 'pretty' work.
    returned_json = pscheduler.json_load(stdout)
    return ok_json(returned_json, sanitize=False)



# Test spec validation
@application.route("/tests/<name>/spec/is-valid", methods=['GET'])
def tests_name_spec_is_valid(name):

    try:
        cursor = dbcursor_query(
            "SELECT EXISTS"
            " (SELECT * FROM test WHERE available AND name = %s)",
            [name])
    except Exception as ex:
        return error(str(ex))

    exists = cursor.fetchone()[0]
    cursor.close()
    if not exists:
        return not_found()

    spec = request.args.get('spec')
    if spec is None:
        return bad_request("No test spec provided")

    try:
        returncode, stdout, stderr = pscheduler.run_program(
            ["pscheduler", "internal", "invoke", "test",
             name, "spec-is-valid"],
            stdin=spec)

        if returncode != 0:
            return error("Unable to validate test spec: %s" % (stderr))

        validate_json = pscheduler.json_load(stdout, max_schema=1)
        return ok_json(validate_json)

    except Exception as ex:
        return error("Unable to validate test spec: %s" % (str(ex)))




# Tools that can carry out test <name>
@application.route("/tests/<name>/tools", methods=['GET'])
def tests_name_tools(name):

    # TODO: Should probably 404 if the test doesn't exist.
    # TODO: Is this used anywhere?

    expanded = is_expanded()
    try:
        cursor = dbcursor_query("""
        SELECT
            tool.name,
            tool.json
        FROM
            tool
            JOIN tool_test ON tool_test.tool = tool.id
            JOIN test ON test.id = tool_test.test
        WHERE
            tool.available
            AND test.name = %s
        """, [name])
    except Exception as ex:
        return error(str(ex))

    result = []
    for row in cursor:
        url = root_url('tools/' + row[0])
        if not expanded:
            result.append(url)
            continue
        row[1]['href'] = url
        result.append(row[1])
    cursor.close()
    return json_response(result)



# Participants in a test spec
@application.route("/tests/<name>/participants", methods=['GET'])
def tests_name_participants(name):

    spec = request.args.get('spec')
    if spec is None:
        return bad_request("No test spec provided")

    # HACK: BWCTLBC -- BEGIN

    lead_bind = request.args.get("lead-bind")

    # Validate the lead binding if there is one.
    if lead_bind is not None \
       and (pscheduler.address_interface(lead_bind) is None):
        return bad_request("Lead bind '%s' is not on this host"
                           % (lead_bind))

    if lead_bind is not None:
        env_add = {"PSCHEDULER_LEAD_BIND_HACK": lead_bind}
    else:
        env_add = None

    # HACK: BWCTLBC --- END

    try:
        returncode, stdout, stderr = pscheduler.run_program(
            [ "pscheduler", "internal", "invoke", "test", name,
              "participants"],
            stdin = spec,
            env_add=env_add   # HACK: BWCTLBC
            )
    except KeyError:
        return bad_request("Invalid spec")
    except Exception as ex:
        return bad_request(ex)

    if returncode != 0:
        return bad_request(stderr)

    # If this fails because of bad JSON, an exception will be thrown,
    # caught and logged.
    return json_response(pscheduler.json_load(stdout, max_schema=1))
