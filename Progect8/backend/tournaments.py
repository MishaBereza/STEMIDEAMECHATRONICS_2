from io import BytesIO
import os
from xml.sax.saxutils import escape

from flask import render_template, flash, redirect, url_for, session, jsonify, send_file, request
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import or_

from .app_helpers import get_current_user
from .models import Team, Tournament
from .translations import get_text


def _t(key, **kwargs):
    return get_text(key, session.get('language', 'en'), **kwargs)


PDF_THEMES = {
    'en': {
        'primary': '#29384F',
        'accent': '#8F3F48',
        'bg': '#F5F2EE',
        'panel': '#FFFFFF',
        'soft': '#F3E9E7',
        'line': '#CBD0D8',
        'text': '#242A34',
        'muted': '#5A6270',
    },
    'uk': {
        'primary': '#2F6FA8',
        'accent': '#C99A35',
        'bg': '#FFF8DB',
        'panel': '#FFFDF2',
        'soft': '#E9F2FA',
        'line': '#B8CBE0',
        'text': '#253142',
        'muted': '#5B6370',
    },
    'it': {
        'primary': '#2D6B3F',
        'accent': '#B94A42',
        'bg': '#FFF7EF',
        'panel': '#FFFAF2',
        'soft': '#EEF6EC',
        'line': '#C9D8C5',
        'text': '#2E2924',
        'muted': '#625D55',
    },
    'de': {
        'primary': '#2F3036',
        'accent': '#B38A32',
        'bg': '#F7F3EB',
        'panel': '#FAF7EF',
        'soft': '#EFE8D9',
        'line': '#D5CCBA',
        'text': '#252525',
        'muted': '#5D5D5F',
    },
    'fr': {
        'primary': '#344F80',
        'accent': '#8B4D64',
        'bg': '#F9F5F6',
        'panel': '#FFFAFC',
        'soft': '#EEF1F8',
        'line': '#CAD2E3',
        'text': '#2A2D36',
        'muted': '#5D6069',
    },
}


def _leaderboard_scores(tournament):
    teams = Team.query.filter_by(tournament_id=tournament.id).all()
    team_scores = []

    for team in teams:
        evaluation_totals = []
        for submission in team.submissions:
            for evaluation in submission.evaluations:
                total = evaluation.total()
                if total > 0:
                    evaluation_totals.append(total)

        total_score = sum(evaluation_totals) if evaluation_totals else 0
        team_scores.append((team, total_score))

    team_scores.sort(key=lambda item: item[1], reverse=True)
    return team_scores


def _register_pdf_fonts():
    fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    regular_candidates = [
        os.path.join(fonts_dir, 'NotoSans-Regular.ttf'),
        r'C:\Windows\Fonts\arialuni.ttf',  # Arial Unicode MS supports all Unicode
        r'C:\Windows\Fonts\arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
    ]
    bold_candidates = [
        os.path.join(fonts_dir, 'NotoSans-Bold.ttf'),
        r'C:\Windows\Fonts\arialbd.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
    ]

    regular_path = next((path for path in regular_candidates if os.path.exists(path)), None)
    bold_path = next((path for path in bold_candidates if os.path.exists(path)), None)

    if not regular_path:
        return 'Helvetica', 'Helvetica-Bold'

    try:
        if 'AppPdfRegular' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('AppPdfRegular', regular_path))
        if bold_path and 'AppPdfBold' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('AppPdfBold', bold_path))
        return 'AppPdfRegular', 'AppPdfBold' if bold_path else 'AppPdfRegular'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'


def _draw_pdf_page(canvas, doc, theme, lang):
    width, height = doc.pagesize
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(theme['bg']))
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor(theme['primary']))
    canvas.rect(0, height - 18, width, 18, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor(theme['accent']))
    canvas.rect(0, height - 23, width, 5, stroke=0, fill=1)
    canvas.setStrokeColor(colors.HexColor(theme['line']))
    canvas.line(doc.leftMargin, 34, width - doc.rightMargin, 34)
    canvas.setFillColor(colors.HexColor(theme['muted']))
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(width - doc.rightMargin, 22, f"{lang.upper()} | {doc.page}")
    canvas.restoreState()


def index():
    filter_type = request.args.get('filter', 'available').strip().lower()
    search = request.args.get('search', '').strip()
    if filter_type not in ('available', 'finished'):
        filter_type = 'available'

    tournaments = Tournament.query.filter_by(is_archived=False).all()

    registration_tournaments_count = Tournament.query.filter(
        or_(
            Tournament.status.ilike('%register%'),
            Tournament.status.ilike('%registration%')
        )
    ).filter_by(is_archived=False).count()

    return render_template(
        'index.html',
        tournaments=tournaments,
        registration_tournaments_count=registration_tournaments_count,
        filter_type=filter_type,
        search=search
    )


def tournament_page(tid):
    t = Tournament.query.get_or_404(tid)
    user = get_current_user()
    myteam = None
    if user:
        myteam = Team.query.filter_by(tournament_id=t.id, captain_id=user.id).first()
        if not myteam:
            for team in user.teams:
                if team.tournament_id == t.id:
                    myteam = team
                    break
    rounds = sorted(t.rounds, key=lambda item: (item.level, item.id))
    round_entries = []

    for round_item in rounds:
        round_is_open = round_item.status.lower() in ('active', 'draft')
        can_submit = False

        if session.get('admin'):
            can_submit = t.status in ['Submission', 'Running'] and round_is_open
        elif user and myteam:
            can_submit = t.status in ['Submission', 'Running'] and round_is_open

        round_entries.append({
            'round': round_item,
            'can_submit': can_submit,
            'can_view_results': bool(myteam and round_item.status == 'Closed'),
        })

    return render_template(
        'tournament.html',
        tournament=t,
        myteam=myteam,
        round_entries=round_entries
    )


def leaderboard(tid):
    t = Tournament.query.get_or_404(tid)
    if t.status.lower() not in ['finished', 'completed', 'closed']:
        flash(_t('leaderboard_only_finished'), 'warning')
        return redirect(url_for('tournament_page', tid=tid))

    team_scores = _leaderboard_scores(t)
    return render_template('leaderboard.html', tournament=t, team_scores=team_scores)


def leaderboard_export_pdf(tid):
    t = Tournament.query.get_or_404(tid)
    if t.status.lower() not in ['finished', 'completed', 'closed']:
        flash(_t('leaderboard_only_finished'), 'warning')
        return redirect(url_for('tournament_page', tid=tid))

    lang = session.get('language', 'en')
    theme = PDF_THEMES.get(lang, PDF_THEMES['en'])
    regular_font, bold_font = _register_pdf_fonts()
    team_scores = _leaderboard_scores(t)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=42,
        leftMargin=42,
        topMargin=52,
        bottomMargin=48,
    )

    title_style = ParagraphStyle(
        name='Title',
        fontName=bold_font,
        fontSize=25,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor(theme['primary']),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        name='Subtitle',
        fontName=regular_font,
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor(theme['muted']),
        spaceAfter=20,
    )
    note_style = ParagraphStyle(
        name='Note',
        fontName=regular_font,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor(theme['muted']),
    )

    elements = [
        Paragraph(_t('app_title'), subtitle_style),
        Paragraph(_t('leaderboard'), title_style),
        Paragraph(t.name, subtitle_style),
        Spacer(1, 10),
    ]

    table_data = [[_t('place'), _t('team'), _t('participants'), _t('total')]]
    for index, (team, score) in enumerate(team_scores, start=1):
        label = team.name
        if index <= 3:
            label = f'{index}. {label}'

        # Build the participants list
        participants = []
        if team.captain:
            participants.append(f"{_t('captain')}: {team.captain.name}")
        for member in team.members:
            if member != team.captain:  # Avoid duplicating the captain
                participants.append(member.name)
        participants_text = ', '.join(participants) if participants else _t('no_teams_to_display')

        table_data.append([str(index), label, participants_text, f'{score:.2f}'])

    table = Table(table_data, colWidths=[40, 180, 180, 70], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(theme['primary'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), bold_font),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), regular_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor(theme['text'])),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor(theme['line'])),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))

    if len(table_data) > 1:
        table.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor(theme['soft']), colors.HexColor(theme['panel'])]),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F5E2A8')),
            ('FONTNAME', (0, 1), (-1, 1), bold_font),
        ]))
    if len(table_data) > 2:
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#E7EAF0')),
        ]))
    if len(table_data) > 3:
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#E9D2BE')),
        ]))

    elements.append(table)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph(escape(_t('pdf_generated_report')), note_style))

    doc.build(
        elements,
        onFirstPage=lambda canvas, doc_obj: _draw_pdf_page(canvas, doc_obj, theme, lang),
        onLaterPages=lambda canvas, doc_obj: _draw_pdf_page(canvas, doc_obj, theme, lang),
    )
    buffer.seek(0)

    filename = f"{t.name.replace('/', '_').replace(' ', '_')}_leaderboard.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


def get_team_details(team_id):
    """API endpoint to get team details for modal display"""
    team = Team.query.get_or_404(team_id)

    captain_info = None
    if team.captain:
        captain_info = {
            'name': team.captain.name,
            'email': team.captain.email,
        }

    members_info = []
    for member in team.members:
        members_info.append({
            'name': member.name,
            'email': member.email,
        })

    submitted_at_str = None
    if team.submitted_at:
        submitted_at_str = team.submitted_at.strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'team_id': team.id,
        'team_name': team.name,
        'captain': captain_info,
        'members': members_info,
        'repo_url': team.repo_url,
        'live_url': team.live_url,
        'comments': team.comments,
        'submission_status': team.submission_status,
        'submitted_at': submitted_at_str,
    })
