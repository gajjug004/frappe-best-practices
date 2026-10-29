#!/usr/bin/env bash
# Usage: verify_http.sh <site> <admin-password> [base-url]
# Needs server scripts enabled. Creates temporary API Server Scripts and deletes them at the end.
set -euo pipefail

site=$1
password=$2
base=${3:-http://127.0.0.1:8000}
jar=$(mktemp)
host="Host: $site"
scripts=(guide_write guide_commit_then_fail guide_fail_no_commit guide_throw guide_raise)

cleanup() {
	for name in "${scripts[@]}"; do
		curl -s -o /dev/null -b "$jar" -H "$host" -X DELETE "$base/api/resource/Server%20Script/$name" || true
	done
	for tag in guide-get guide-post guide-first guide-second guide-nocommit; do
		for name in $(curl -s -b "$jar" -H "$host" -G "$base/api/resource/ToDo" \
			--data-urlencode "filters=[[\"description\",\"=\",\"$tag\"]]" | python3 -c 'import json,sys;print(" ".join(d["name"] for d in json.load(sys.stdin)["data"]))'); do
			curl -s -o /dev/null -b "$jar" -H "$host" -X DELETE "$base/api/resource/ToDo/$name"
		done
	done
	rm -f "$jar"
}
trap cleanup EXIT

curl -s -o /dev/null -c "$jar" -H "$host" -X POST "$base/api/method/login" -d usr=Administrator -d "pwd=$password"

create_script() {
	python3 -c 'import json,sys;print(json.dumps({"name":sys.argv[1],"script_type":"API","api_method":sys.argv[1],"script":sys.argv[2]}))' "$1" "$2" |
		curl -s -o /dev/null -b "$jar" -H "$host" -H "Content-Type: application/json" -X POST "$base/api/resource/Server%20Script" --data @-
}

create_script guide_write 'frappe.get_doc({"doctype":"ToDo","description":frappe.form_dict.tag}).insert()'
create_script guide_commit_then_fail 'frappe.get_doc({"doctype":"ToDo","description":"guide-first"}).insert()
frappe.db.commit()
frappe.get_doc({"doctype":"ToDo","description":"guide-second"}).insert()
frappe.throw("Something failed")'
create_script guide_fail_no_commit 'frappe.get_doc({"doctype":"ToDo","description":"guide-nocommit"}).insert()
frappe.throw("Something failed")'
create_script guide_throw 'frappe.throw("Customer is required")'
create_script guide_raise 'x = 1 / 0'

status() { curl -s -o /dev/null -w "%{http_code}" -b "$jar" -H "$host" "$@"; }
count() {
	curl -s -b "$jar" -H "$host" -G "$base/api/method/frappe.client.get_count" -d doctype=ToDo \
		--data-urlencode "filters={\"description\":\"$1\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["message"])'
}
check() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1 (got $2, want $3)"; fi; }

status "$base/api/method/guide_write?tag=guide-get" >/dev/null
status -X POST "$base/api/method/guide_write" -d tag=guide-post >/dev/null
status -X POST "$base/api/method/guide_commit_then_fail" >/dev/null
status -X POST "$base/api/method/guide_fail_no_commit" >/dev/null

check "GET write is rolled back" "$(count guide-get)" 0
check "POST write is saved" "$(count guide-post)" 1
check "write before manual commit survives the error" "$(count guide-first)" 1
check "write after manual commit is lost" "$(count guide-second)" 0
check "error without commit saves nothing" "$(count guide-nocommit)" 0
check "frappe.throw returns 417" "$(status -X POST "$base/api/method/guide_throw")" 417
check "uncaught error returns 500" "$(status -X POST "$base/api/method/guide_raise")" 500
check "frappe.throw sends _server_messages" \
	"$(curl -s -b "$jar" -H "$host" -X POST "$base/api/method/guide_throw" | python3 -c 'import json,sys;print("_server_messages" in json.load(sys.stdin))')" True
check "uncaught error sends no _server_messages" \
	"$(curl -s -b "$jar" -H "$host" -X POST "$base/api/method/guide_raise" | python3 -c 'import json,sys;print("_server_messages" in json.load(sys.stdin))')" False

html_tag() { curl -s -H "$host" "$@" "$base/login" | grep -o '<html[^>]*>'; }
check "guest Accept-Language ar is right to left" "$(html_tag -H 'Accept-Language: ar')" '<html lang="ar" dir="rtl">'
check "regional ar-SA falls back to ar" "$(html_tag -H 'Accept-Language: ar-SA')" '<html lang="ar" dir="rtl">'
check "guest Accept-Language en is left to right" "$(html_tag -H 'Accept-Language: en')" '<html lang="en" dir="ltr">'
check "preferred_language cookie beats Accept-Language" \
	"$(html_tag -b preferred_language=fa -H 'Accept-Language: ar')" '<html lang="fa" dir="rtl">'
