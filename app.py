"""
CareerGap AI - prototype backend
Rule-based skill-gap analysis, weighted readiness scoring, adaptive roadmap
generation, project recommendation, and a role-specific skill assessment.
"""

import json
import os

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "careergap-ai-dev-secret"  # fine for a local prototype/demo

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "roles.json")

# Proficiency -> how much credit a skill gets toward the readiness score.
PROFICIENCY_WEIGHTS = {
    "not_known": 0.0,
    "beginner": 0.5,
    "intermediate": 0.8,
    "advanced": 1.0,
}

PROFICIENCY_LABELS = {
    "not_known": "Not known",
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}


def load_roles():
    with open(DATA_PATH, "r") as f:
        return json.load(f)


ROLES = load_roles()


def build_result(role, profile):
    """Core skill-gap engine: turns a role + a skill/proficiency profile
    into known/missing/improve buckets, a weighted readiness score,
    a prioritized gap list, and an adaptive roadmap."""

    known, missing, improve = [], [], []
    critical_gaps, important_gaps, other_gaps = [], [], []
    total_weight = 0
    earned_weight = 0

    for skill in role["skills"]:
        level = profile.get(skill["id"], "not_known")
        factor = PROFICIENCY_WEIGHTS.get(level, 0.0)

        total_weight += skill["importance"]
        earned_weight += skill["importance"] * factor

        entry = {**skill, "level": level, "level_label": PROFICIENCY_LABELS.get(level, level)}

        if level == "not_known":
            missing.append(entry)
            if skill["importance"] >= 4:
                critical_gaps.append(entry)
            elif skill["importance"] == 3:
                important_gaps.append(entry)
            else:
                other_gaps.append(entry)
        elif level == "beginner":
            improve.append(entry)
            known.append(entry)
        else:
            known.append(entry)

    readiness = round((earned_weight / total_weight) * 100) if total_weight else 0

    # Adaptive roadmap: only the skills from the role's learning sequence
    # that the student hasn't already mastered ("advanced").
    roadmap = []
    for skill_id in role["roadmap"]:
        level = profile.get(skill_id, "not_known")
        if level != "advanced":
            skill = next(s for s in role["skills"] if s["id"] == skill_id)
            roadmap.append({**skill, "level": level, "level_label": PROFICIENCY_LABELS.get(level, level)})

    next_skill = roadmap[0] if roadmap else None

    return {
        "known": known,
        "missing": missing,
        "improve": improve,
        "critical_gaps": critical_gaps,
        "important_gaps": important_gaps,
        "other_gaps": other_gaps,
        "readiness": readiness,
        "roadmap": roadmap,
        "next_skill": next_skill,
        "project": role["project"],
    }


@app.route("/")
def home():
    return render_template("index.html", roles=ROLES)


@app.route("/api/role/<role_id>")
def get_role_skills(role_id):
    role = ROLES.get(role_id)
    if not role:
        return {"error": "Role not found"}, 404
    return {"skills": role["skills"]}


@app.route("/analyze", methods=["POST"])
def analyze():
    role_id = request.form.get("role")
    role = ROLES.get(role_id)
    if not role:
        return redirect(url_for("home"))

    profile = {
        skill["id"]: request.form.get(f"skill_{skill['id']}", "not_known")
        for skill in role["skills"]
    }

    # Stored so the assessment step can update the same profile later.
    session["role_id"] = role_id
    session["profile"] = profile

    result = build_result(role, profile)
    return render_template("result.html", role=role, role_id=role_id, result=result)


@app.route("/assessment/<role_id>")
def assessment(role_id):
    role = ROLES.get(role_id)
    if not role:
        return redirect(url_for("home"))
    return render_template("assessment.html", role=role, role_id=role_id)


@app.route("/assessment/<role_id>/submit", methods=["POST"])
def submit_assessment(role_id):
    role = ROLES.get(role_id)
    if not role:
        return redirect(url_for("home"))

    questions = role["assessment"]
    score = 0
    verified, needs_work = [], []

    for i, q in enumerate(questions):
        chosen = request.form.get(f"q{i}")
        if chosen == q["answer"]:
            score += 1
            verified.append(q["skill"])
        else:
            needs_work.append(q["skill"])

    # Bump verified skills to at least "intermediate" in the stored profile,
    # so the readiness dashboard reflects what the student just proved.
    profile = session.get("profile", {})
    for skill_id in verified:
        current = profile.get(skill_id, "not_known")
        if PROFICIENCY_WEIGHTS.get(current, 0) < PROFICIENCY_WEIGHTS["intermediate"]:
            profile[skill_id] = "intermediate"
    session["profile"] = profile

    result = build_result(role, profile) if profile else None
    skill_lookup = {s["id"]: s["name"] for s in role["skills"]}

    return render_template(
        "assessment_result.html",
        role=role,
        role_id=role_id,
        score=score,
        total=len(questions),
        verified_names=[skill_lookup.get(s, s) for s in verified],
        needs_work_names=[skill_lookup.get(s, s) for s in needs_work],
        result=result,
    )


if __name__ == "__main__":
    app.run(debug=True)
