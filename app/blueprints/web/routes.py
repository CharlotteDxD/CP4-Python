from flask import Blueprint, redirect, render_template, url_for

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def raiz():
    return redirect(url_for("web.painel"))


@web_bp.route("/app")
def painel():
    return render_template("painel.html")


@web_bp.route("/app/transacoes")
def transacoes():
    return render_template("transacoes.html")


@web_bp.route("/app/alertas")
def alertas():
    return render_template("alertas.html")


@web_bp.route("/app/categorias")
def categorias():
    return render_template("categorias.html")
