import os
import random
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, abort, jsonify
from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10


def get_start_and_end(request):
    # a reusable pagination function to return start and end values
    data = dict()
    page = request.args.get("page", 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE
    data["start"] = start
    data["end"] = end
    return data


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)
    CORS(app)

    @app.after_request
    def after_request(response):
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add(
            "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"
        )
        return response

    @app.route("/categories", methods=["GET"])
    def get_categories():
        categories = Category.query.all()
        if len(categories) == 0:
            abort(404)
        else:
            formatted_categories = [category.format() for category in categories]
            data = dict()
            # iterate over the results of formatted_categories and create key of id
            # with value of type in the dictionary
            for category in formatted_categories:
                data[category["id"]] = category["type"]
            return jsonify(
                {
                    "success": True,
                    "categories": data,
                }
            )

    @app.route("/questions", methods=["GET"])
    def get_questions():
        pagination = get_start_and_end(request)
        start = pagination["start"]
        end = pagination["end"]
        questions = Question.query.order_by(Question.id).all()
        if len(questions) == 0:
            abort(404)
        else:
            formatted_questions = [question.format() for question in questions]
            data = dict()
            # add questions key to the dictionary with value of
            # formatted_questions
            data["questions"] = formatted_questions[start:end]
            data["total_questions"] = len(formatted_questions)
            categories = Category.query.all()
            formatted_categories = [category.format() for category in categories]
            # add categories to the dictionary
            data["categories"] = dict()
            # iterate over the results of formatted_categories and
            # create key of id with value of type in the dictionary on the
            # categories key
            for category in formatted_categories:
                data["categories"][category["id"]] = category["type"]
            # https://knowledge.udacity.com/questions/809673 set current_category to
            # empty value per Udacity mentor as there is more than one category
            # returned for all questions
            data["current_category"] = None
            data["success"] = True
            return jsonify(data)

    @app.route("/questions/<int:question_id>", methods=["DELETE"])
    def delete_question(question_id):
        try:
            question = Question.query.filter(Question.id == question_id).one_or_none()
            if question is None:
                abort(404)
            question.delete()
            return jsonify(success=True)
        except Exception as e:
            abort(422)

    @app.route("/questions", methods=["POST"])
    def add_question():
        try:
            data = request.get_json()
            question = data["question"]
            answer = data["answer"]
            difficulty = data["difficulty"]
            category = data["category"]
            # create new Question object, and call insert
            new_question = Question(
                question=question,
                answer=answer,
                category=category,
                difficulty=difficulty,
            )
            new_question.insert()
            return jsonify(success=True)
        except Exception as e:
            abort(422)

    @app.route("/questions/search", methods=["POST"])
    def search_questions():
        pagination = get_start_and_end(request)
        start = pagination["start"]
        end = pagination["end"]
        try:
            data = request.get_json()

            # lowercase the seach term and use ilike to allow for a case
            # insensitive query
            search_term = data["searchTerm"].lower()
            questions = (
                Question.query.filter(Question.question.ilike("%" + search_term + "%"))
                .order_by(Question.id)
                .all()
            )

            if len(questions) == 0:
                abort(404)

            formatted_questions = [question.format() for question in questions]
            data = dict()
            data["questions"] = formatted_questions[start:end]
            data["total_questions"] = len(formatted_questions)
            # https://knowledge.udacity.com/questions/809673 set to empty value per Udacity mentor
            # as there can be more than one category returned for the search
            # term
            data["current_category"] = None
            data["success"] = True
            return jsonify(data)
        except Exception as e:
            abort(400)

    @app.route("/categories/<int:category_id>/questions", methods=["GET"])
    def get_questions_by_category(category_id):
        pagination = get_start_and_end(request)
        start = pagination["start"]
        end = pagination["end"]
        try:
            category = Category.query.filter(Category.id == category_id).one_or_none()
            # set current_category to empty val if category is None, otherwise
            # set to category type
            current_category = None if category is None else category.format()["type"]
            # cast int to str as category id is an int on the category model
            # and a str on the question model
            questions = Question.query.filter(
                Question.category == str(category_id)
            ).all()

            if len(questions) == 0:
                abort(404)

            formatted_questions = [question.format() for question in questions]
            data = dict()
            data["questions"] = formatted_questions[start:end]
            data["total_questions"] = len(formatted_questions)
            data["current_category"] = current_category
            data["success"] = True
            return jsonify(data)
        except Exception as e:
            abort(422)

    @app.route("/quizzes", methods=["POST"])
    def get_questions_for_quiz():
        try:
            data = request.get_json()
            previous_questions = data["previous_questions"]
            quiz_category = data["quiz_category"]
            category_id = quiz_category["id"]
            # account for user choosing all categories
            if category_id == 0:
                questions = Question.query.all()
            else:
                questions = Question.query.filter(
                    Question.category == category_id
                ).all()

            if len(questions) == 0:
                abort(404)

            formatted_questions = [question.format() for question in questions]
            non_previous_questions = []
            # iterate over the questions and if the question id in iteration is not in previous questions arr
            # append to the non_previous_questions arr
            for question in formatted_questions:
                if question["id"] not in previous_questions:
                    non_previous_questions.append(question)
            num_questions = len(non_previous_questions)

            # pick a random number in the range of the len of the
            # non_previous_questions arr - 1
            random_idx = random.randint(0, num_questions - 1)
            random_question = non_previous_questions[random_idx]
            return jsonify({"success": True, "question": random_question})
        except Exception as e:
            abort(422)

    @app.errorhandler(400)
    def invalid_request(error):
        return (
            jsonify({"success": False, "error": 400, "message": "Invalid request"}),
            400,
        )

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": 404, "message": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return (
            jsonify({"success": False, "error": 405, "message": "Method not allowed"}),
            405,
        )

    @app.errorhandler(422)
    def not_processable(error):
        return (
            jsonify(
                {"success": False, "error": 422, "message": "Unprocessable content"}
            ),
            422,
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        return (
            jsonify(
                {"success": False, "error": 500, "message": "Internal server error"}
            ),
            500,
        )

    return app
