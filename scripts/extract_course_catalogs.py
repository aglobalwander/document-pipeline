#!/usr/bin/env python3
"""
Extract structured course data from SAS PDHS and PXHS 2026-27 course catalog PDFs.
Outputs JSON with full course details: name, codes, credits, grades, department,
prerequisites, description, main_topics, learning_outcomes.
"""

import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


# ── Master Course List Data ──────────────────────────────────────────────────
# Manually transcribed from the master course list tables (pages 8-10 PDHS, 11-14 PXHS)
# Format: (course_name, course_codes, credits, grades, department)

PDHS_MASTER = [
    # ENGLISH
    ("English 9", ["HS1000"], 1, "9", "English"),
    ("English 10", ["HS1001"], 1, "10", "English"),
    ("English 11", ["HS1002"], 1, "11", "English"),
    ("English 12", ["HS1003"], 1, "12", "English"),
    ("Literature and Film", ["HS1405"], 1, "10,11,12", "English"),
    ("AP English Language & Composition", ["HS1200"], 1, "11,12", "English"),
    ("AP English Literature & Composition", ["HS1201"], 1, "12", "English"),
    ("IB English A: Literature SL Y1-Y2", ["HS1110", "HS1120"], 2, "11,12", "English"),
    ("IB English A: Literature HL Y1-Y2", ["HS1130", "HS1140"], 2, "11,12", "English"),
    ("IB English A: Language & Literature SL Y1-Y2", ["HS1111", "HS1121"], 2, "11,12", "English"),
    ("IB English A: Language & Literature HL Y1-Y2", ["HS1131", "HS1141"], 2, "11,12", "English"),
    # SOCIAL STUDIES
    ("Asian History", ["HS2000"], 1, "9", "Social Studies"),
    ("Modern World History", ["HS2001"], 1, "10,11,12", "Social Studies"),
    ("US History", ["HS2002"], 1, "10,11,12", "Social Studies"),
    ("Sociology", ["HS2009"], 1, "10,11,12", "Social Studies"),
    ("AP US Government and Politics", ["HS22090"], 1, "11,12", "Social Studies"),
    ("AP US History", ["HS2202"], 1, "10,11,12", "Social Studies"),
    ("AP Psychology", ["HS2203"], 1, "11,12", "Social Studies"),
    ("AP Economics", ["HS2204"], 1, "11,12", "Social Studies"),
    ("AP World History", ["HS2206"], 1, "10,11,12", "Social Studies"),
    ("AP Human Geography", ["HS2207"], 1, "10,11,12", "Social Studies"),
    ("IB Economics SL Y1-Y2", ["HS2114", "HS2124"], 2, "11,12", "Social Studies"),
    ("IB Economics HL Y1-Y2", ["HS2134", "HS2144"], 2, "11,12", "Social Studies"),
    ("IB Business Management SL Y1-Y2", ["HS2117", "HS2127"], 2, "11,12", "Social Studies"),
    ("IB Business Management HL Y1-Y2", ["HS2137", "HS2147"], 2, "11,12", "Social Studies"),
    ("IB Psychology SL Y1-Y2", ["HS2113", "HS2123"], 2, "11,12", "Social Studies"),
    ("IB Psychology HL Y1-Y2", ["HS2133", "HS2143"], 2, "11,12", "Social Studies"),
    ("IB Environmental Systems & Societies SL Y1-Y2", ["HS4115", "HS4125"], 1, "11,12", "Social Studies"),
    ("IB Global Politics SL Y1-Y2", ["HS2153", "HS2154"], 2, "11,12", "Social Studies"),
    ("IB Global Politics HL Y1-Y2", ["HS2163", "HS2164"], 2, "11,12", "Social Studies"),
    # MATHEMATICS
    ("Integrated Math 1 (IM1)", ["HS3203"], 1, "9,10,11,12", "Mathematics"),
    ("Integrated Math 2 (IM2)", ["HS3205"], 1, "9,10,11,12", "Mathematics"),
    ("Integrated Math 2+ (IM2+)", ["HS3205A"], 1, "9,10,11,12", "Mathematics"),
    ("Integrated Math 3 (IM3)", ["HS3207"], 1, "9,10,11,12", "Mathematics"),
    ("Integrated Math 3+ (IM3+)", ["HS3208"], 1, "9,10,11,12", "Mathematics"),
    ("Statistical Math", ["HS3007"], 1, "9,10,11,12", "Mathematics"),
    ("Pre-Calculus", ["HS3011"], 1, "9,10,11,12", "Mathematics"),
    ("AP Pre-Calculus", ["HS3012"], 1, "9,10,11,12", "Mathematics"),
    ("AP Calculus AB", ["HS3200"], 1, "9,10,11,12", "Mathematics"),
    ("AP Calculus BC", ["HS3201"], 1, "9,10,11,12", "Mathematics"),
    ("AP Statistics", ["HS3202"], 1, "9,10,11,12", "Mathematics"),
    ("Multivariable Calculus", ["HS3204"], 1, "9,10,11,12", "Mathematics"),
    ("IB Math: Application and Interpretation SL Y1-Y2", ["HS3113", "HS3123"], 2, "11,12", "Mathematics"),
    ("IB Math: Application and Interpretation HL Y1-Y2", ["HS3133", "HS3143"], 2, "11,12", "Mathematics"),
    ("IB Math: Analysis and Approaches SL Y1-Y2", ["HS3114", "HS3124"], 2, "11,12", "Mathematics"),
    ("IB Math: Analysis and Approaches HL Y1-Y2", ["HS3134", "HS3144"], 2, "11,12", "Mathematics"),
    # SCIENCE
    ("Physics/Chemistry Lab Science", ["HS4007"], 1, "9", "Science"),
    ("Biology Lab Science", ["HS4008"], 1, "10", "Science"),
    ("Chemistry", ["HS4004"], 1, "11,12", "Science"),
    ("Earth & Space Science", ["HS4029"], 1, "11,12", "Science"),
    ("AP Biology", ["HS4200"], 1, "10,11,12", "Science"),
    ("AP Chemistry", ["HS4201"], 1, "11,12", "Science"),
    ("AP Physics 1", ["HS4210"], 1, "11,12", "Science"),
    ("AP Environmental Science", ["HS4203"], 1, "11,12", "Science"),
    ("AP Physics C: Mechanics", ["HS4208"], 1, "11,12", "Science"),
    ("AP Physics C: Electricity & Magnetism", ["HS4209"], 1, "12", "Science"),
    ("IB Biology SL Y1-Y2", ["HS4110", "HS4120"], 2, "11,12", "Science"),
    ("IB Biology HL Y1-Y2", ["HS4130", "HS4140"], 2, "11,12", "Science"),
    ("IB Chemistry SL Y1-Y2", ["HS4111", "HS4121"], 2, "11,12", "Science"),
    ("IB Chemistry HL Y1-Y2", ["HS4131", "HS4141"], 2, "11,12", "Science"),
    ("IB Environmental Systems & Societies SL Y1-Y2", ["HS4115", "HS4125"], 2, "11,12", "Science"),
    ("IB Physics SL Y1-Y2", ["HS4112", "HS4122"], 2, "11,12", "Science"),
    ("IB Physics HL Y1-Y2", ["HS4132", "HS4142"], 2, "11,12", "Science"),
    # CHINESE LANGUAGE
    ("Novice Chinese", ["HS5024A"], 1, "9,10,11,12", "Chinese Language"),
    ("Intermediate Low Chinese", ["HS5025A"], 1, "9,10,11,12", "Chinese Language"),
    ("Intermediate Mid Chinese", ["HS5026"], 1, "9,10,11,12", "Chinese Language"),
    ("Intermediate High Chinese", ["HS3033"], 1, "9,10,11,12", "Chinese Language"),
    ("Advanced Low Chinese", ["HS5031"], 1, "9,10,11,12", "Chinese Language"),
    ("Advanced Mid Chinese", ["HS5032"], 1, "9,10,11,12", "Chinese Language"),
    ("Advanced High Chinese", ["HS3034"], 1, "9,10,11,12", "Chinese Language"),
    ("Superior Chinese", ["HS5147"], 1, "11,12", "Chinese Language"),
    ("Superior Chinese 2", ["HS5149A"], None, "12", "Chinese Language"),
    ("IB Mandarin Ab Initio SL Y1-Y2", ["HS5159", "HS5150"], 2, "11,12", "Chinese Language"),
    ("IB Mandarin B SL Y1-Y2", ["HS5113", "HS5123"], 2, "11,12", "Chinese Language"),
    ("IB Mandarin B HL Y1-Y2", ["HS5133", "HS5143"], 2, "11,12", "Chinese Language"),
    ("IB Chinese A: Language & Literature SL Y1-Y2", ["HS5114", "HS5124"], 2, "11,12", "Chinese Language"),
    ("IB Chinese A: Language & Literature HL Y1-Y2", ["HS5134", "HS5144"], 2, "11,12", "Chinese Language"),
    # GLOBAL LANGUAGES
    ("French Novice", ["HS2001"], 1, "9,10,11,12", "Global Languages"),
    ("French Intermediate Mid", ["HS5002"], 1, "9,10,11,12", "Global Languages"),
    ("French Intermediate High", ["HS5003"], 1, "9,10,11,12", "Global Languages"),
    ("French Advanced Low", ["HS5004"], 1, "9,10,11,12", "Global Languages"),
    ("French Advanced Mid", ["HS5022"], 1, "9,10,11,12", "Global Languages"),
    ("IB French Ab Initio Y1-Y2", ["HS5151", "HS5152"], 2, "11,12", "Global Languages"),
    ("IB French B SL Y1-Y2", ["HS5110", "HS5120"], 2, "11,12", "Global Languages"),
    ("IB French B HL Y1-Y2", ["HS5130", "HS5140"], 2, "11,12", "Global Languages"),
    ("Spanish Novice", ["HS5005"], 1, "9,10,11,12", "Global Languages"),
    ("Spanish Intermediate Mid", ["HS5006"], 1, "9,10,11,12", "Global Languages"),
    ("Spanish Intermediate High", ["HS5007"], 1, "9,10,11,12", "Global Languages"),
    ("Spanish Advanced Low", ["HS5008"], 1, "9,10,11,12", "Global Languages"),
    ("Spanish Advanced Mid", ["HS5021"], 1, "9,10,11,12", "Global Languages"),
    ("IB Spanish Ab Initio Y1-Y2", ["HS5155", "HS5156"], 2, "11,12", "Global Languages"),
    ("IB Spanish B SL Y1-Y2", ["HS5111", "HS5121"], 2, "11,12", "Global Languages"),
    ("IB Spanish B HL Y1-Y2", ["HS5131", "HS5141"], 2, "11,12", "Global Languages"),
    ("IB Self-Taught Language A1 SL Y1-Y2", ["HS5102", "HS5103"], 2, "11,12", "Global Languages"),
    # VISUAL ARTS
    ("Art Foundations", ["HS6001"], 1, "9,10,11,12", "Visual Arts"),
    ("Studio Art", ["HS6014"], 1, "10,11,12", "Visual Arts"),
    ("Advanced Studio Art 1", ["HS6007"], 1, "11,12", "Visual Arts"),
    ("Advanced Studio Art 2", ["HS6008"], 1, "12", "Visual Arts"),
    ("Photography", ["HS6035"], 1, "9,10,11,12", "Visual Arts"),
    ("Advanced Photography 1, 2, 3", ["HS6012", "HS6012B", "HS6012C"], 1, "10,11,12", "Visual Arts"),
    ("Creativity and Design (Inno G9)", ["HS6050"], 1, "9", "Visual Arts"),
    ("Innovation & Design (Inno G10)", ["HS6051"], 1, "10", "Visual Arts"),
    ("AP 2D Design", ["HS6202"], 1, "11,12", "Visual Arts"),
    ("IB Visual Arts SL Y1-Y2", ["HS6110", "HS6120"], 2, "11,12", "Visual Arts"),
    ("IB Visual Arts HL Y1-Y2", ["HS6130", "HS6140"], 2, "11,12", "Visual Arts"),
    ("Digital Film Making", ["HS8001"], 1, "9,10,11,12", "Visual Arts"),
    ("Advanced Digital Film Making 1,2,3", ["HS8005", "HS8005B", "HS8005C"], 1, "10,11,12", "Visual Arts"),
    ("IB Film SL Y1-Y2", ["HS8165", "HS8175"], 2, "11,12", "Visual Arts"),
    ("IB Film HL Y1-Y2", ["HS8185", "HS8195"], 2, "11,12", "Visual Arts"),
    ("Graphic Design", ["HS8010"], 1, "9,10,11,12", "Visual Arts"),
    ("Advanced Graphic Design 1, 2, 3", ["HS8010A", "HS8010B", "HS8010C"], 1, "10,11,12", "Visual Arts"),
    # PERFORMING ARTS
    ("Contemporary Music", ["HS1404"], 1, "9,10,11,12", "Performing Arts"),
    ("Advanced Contemporary Music", ["HS1404B"], 1, "10,11,12", "Performing Arts"),
    ("Advanced Choir", ["HS6041"], 1, "9,10,11,12", "Performing Arts"),
    ("Concert Band: Beginning", ["HS6039"], 1, "9", "Performing Arts"),
    ("Concert Band: Intermediate", ["HS6042"], 1, "9,10,11,12", "Performing Arts"),
    ("Concert Band: Advanced", ["HS6043"], 1, "9,10,11,12", "Performing Arts"),
    ("Orchestra: Prelude", ["HS6054"], 1, "9,10", "Performing Arts"),
    ("Orchestra: Intermezzo", ["HS6056"], 1, "9,10", "Performing Arts"),
    ("Orchestra: Finale", ["HS6055"], 1, "9,10,11,12", "Performing Arts"),
    ("Orchestra: Advanced", ["HS6045"], 1, "9,10,11,12", "Performing Arts"),
    ("Theatre Design", ["HS6059"], 1, "9,10,11,12", "Performing Arts"),
    ("Advance Theatre Design", ["HS6060"], 1, "10,11,12", "Performing Arts"),
    ("Theatre 1", ["HS6057"], 1, "9,10,11,12", "Performing Arts"),
    ("Theatre 2", ["HS6058"], 1, "10,11,12", "Performing Arts"),
    ("Dance 1", ["HS7010"], 1, "9,10,11,12", "Performing Arts"),
    ("Dance 2", ["HS7011"], 1, "9,10,11,12", "Performing Arts"),
    ("IB Dance SL Y1-Y2", ["HS7013", "HS7033"], 2, "11,12", "Performing Arts"),
    ("IB Dance HL Y1-Y2", ["HS7023", "HS7043"], 2, "11,12", "Performing Arts"),
    ("IB Music SL Y1-Y2", ["HS6111", "HS6121"], 2, "11", "Performing Arts"),
    ("IB Music HL Y1-Y2", ["HS6131", "HS6141"], 2, "11", "Performing Arts"),
    ("IB Theatre SL Y1-Y2", ["HS6112", "HS6122"], 2, "11,12", "Performing Arts"),
    ("IB Theatre HL Y1-Y2", ["HS6132", "HS6142"], 2, "11,12", "Performing Arts"),
    # APPLIED ARTS
    ("Electrical and Mechanical Design", ["HS6066"], 1.0, "9,10,11,12", "Applied Arts"),
    ("Engineering and Robotics", ["HS6067"], 1.0, "9,10,11,12", "Applied Arts"),
    # GTAE PATHWAY
    ("Introduction to Robotics (Robotics & Automation)", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Product Design & Manufacturing", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Physical Computing", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Python Programming for Engineers", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Fundamentals of Game Development", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Fundamentals of Applied Engineering", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Design Theory", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Engineering Capstone", ["HS8406"], 1, "11,12", "GTAE Pathway"),
    # PHYSICAL AND HEALTH EDUCATION
    ("Physical & Health Education 1", ["HS7000"], 1, "9", "Physical and Health Education"),
    ("Physical & Health Education 2", ["HS7001"], 1, "10", "Physical and Health Education"),
    ("Physical & Health Education 3 - Personal Fitness", ["HS7004"], 1, "11,12", "Physical and Health Education"),
    ("PE 3 - Water Safety Instructor", ["HS7006"], 0.5, "11,12", "Physical and Health Education"),
    ("PE 3 - Lifeguarding", ["HS7007"], 0.5, "11,12", "Physical and Health Education"),
    # OTHER COURSES
    ("IB Theory of Knowledge Y1-Y2", ["HS8101", "HS8102"], 1, "11,12", "Other Courses"),
    ("AP Computer Science A", ["HS8201"], 1, "10,11,12", "Other Courses"),
    ("AP Computer Science Principles", ["HS8204"], 1, "9,10,11,12", "Other Courses"),
    ("AP Capstone Seminar", ["HS8202"], 1, "10,11", "Other Courses"),
    ("AP Capstone Research", ["HS8203"], 1, "11,12", "Other Courses"),
    ("IB Computer Science SL Y1-Y2", ["HS8115"], 1, "11,12", "Other Courses"),
    ("IB Computer Science HL Y1-Y2", ["HS8135"], 1, "11,12", "Other Courses"),
]

PXHS_MASTER = [
    # ENGLISH
    ("English 9", ["HS1000"], 1, "9", "English"),
    ("English 10", ["HS1001"], 1, "10", "English"),
    ("Literature in Film", ["HS1405"], 1, "10,11,12", "English"),
    ("English 11", ["HS1002"], 1, "11", "English"),
    ("English 12", ["HS1003"], 1, "12", "English"),
    ("IB English A: Literature SL Y1-Y2", ["HS1110", "HS1120"], 2, "11,12", "English"),
    ("IB English A: Literature HL Y1-Y2", ["HS1130", "HS1140"], 2, "11,12", "English"),
    ("IB English A: Language & Literature SL Y1-Y2", ["HS1111", "HS1121"], 2, "11,12", "English"),
    ("IB English A: Language & Literature HL Y1-Y2", ["HS1131", "HS1141"], 2, "11,12", "English"),
    ("AP English Language & Composition", ["HS1200"], 1, "11,12", "English"),
    # MATHEMATICS
    ("Integrated Math 1 (IM1)", ["HS3203"], 1, "9", "Mathematics"),
    ("Integrated Math 2 (IM2)", ["HS3205"], 1, "9,10,11", "Mathematics"),
    ("Integrated Math 3 (IM3)", ["HS3207"], 1, "10,11,12", "Mathematics"),
    ("Integrated Math 3 Plus (IM3+)", ["HS3208"], 1, "9,10,11,12", "Mathematics"),
    ("Integrated Math 3 Plus E", ["HS3209"], 1, "9,10", "Mathematics"),
    ("Pre-Calculus", ["HS3011"], 1, "11,12", "Mathematics"),
    ("AP Pre-Calculus", ["HS3003"], 1, "10,11", "Mathematics"),
    ("Calculus", ["HS3006"], 1, "10,11,12", "Mathematics"),
    ("IB Mathematics Application and Interpretation SL Y1-Y2", ["HS3113", "HS3123"], 1, "11,12", "Mathematics"),
    ("IB Mathematics Application and Interpretation HL Y1-Y2", ["HS3133", "HS3143"], 1, "11,12", "Mathematics"),
    ("IB Mathematics Analysis and Approaches SL Y1-Y2", ["HS3114", "HS3124"], 1, "11,12", "Mathematics"),
    ("IB Mathematics Analysis and Approaches HL Y1-Y2", ["HS3134", "HS3144"], 1, "11,12", "Mathematics"),
    ("AP Calculus AB", ["HS3200"], 1, "11,12", "Mathematics"),
    ("AP Calculus BC", ["HS3201"], 1, "11,12", "Mathematics"),
    ("AP Statistics", ["HS3202"], 1, "11,12", "Mathematics"),
    ("Multivariable Calculus & Series", ["HS3204"], 1, "11,12", "Mathematics"),
    # SOCIAL STUDIES
    ("Asian History", ["HS2000"], 1, "9", "Social Studies"),
    ("US History", ["HS2002"], 1, "10,11,12", "Social Studies"),
    ("Sociology", ["HS2009"], 1, "10,11,12", "Social Studies"),
    ("Applied Economics & Business", ["HS2018"], 1, "10,11,12", "Social Studies"),
    ("Historical Inquiry", ["HS2014"], 1, "11,12", "Social Studies"),
    ("IB History SL Y1-Y2", ["HS2111", "HS2121"], 2, "11,12", "Social Studies"),
    ("IB History HL Y1-Y2", ["HS2131", "HS2141"], 2, "11,12", "Social Studies"),
    ("IB Philosophy SL Y1-Y2", ["HS2145", "HS2146"], 2, "11,12", "Social Studies"),
    ("IB Environmental Systems & Society SL Y1-Y2", ["HS4115", "HS4125"], 1, "11,12", "Social Studies"),
    ("IB Psychology SL Y1-Y2", ["HS2113", "HS2123"], 2, "11,12", "Social Studies"),
    ("IB Psychology HL Y1-Y2", ["HS2133", "HS2143"], 2, "11,12", "Social Studies"),
    ("IB Economics SL Y1-Y2", ["HS2114", "HS2124"], 2, "11,12", "Social Studies"),
    ("IB Economics HL Y1-Y2", ["HS2134", "HS2144"], 2, "11,12", "Social Studies"),
    ("IB Global Politics SL Y1-Y2", ["HS2153"], 1, "11,12", "Social Studies"),
    ("IB Global Politics HL Y1-Y2", ["HS2163"], 1, "11,12", "Social Studies"),
    ("IB Business & Management SL Y1-Y2", ["HS2117", "HS2127"], 2, "11,12", "Social Studies"),
    ("IB Business & Management HL Y1-Y2", ["HS2137", "HS2147"], 2, "11,12", "Social Studies"),
    ("AP Capstone Seminar: Social Studies", ["HS2208"], 1, "10,11,12", "Social Studies"),
    ("AP European History", ["HS2201"], 1, "10,11,12", "Social Studies"),
    ("AP US History", ["HS2202"], 1, "10,11,12", "Social Studies"),
    ("AP World History: Modern", ["HS2206"], 1, "10,11,12", "Social Studies"),
    ("AP Psychology", ["HS2203"], 1, "11,12", "Social Studies"),
    ("AP Microeconomics", ["HS2209"], 1, "11,12", "Social Studies"),
    ("AP Macroeconomics", ["HS2210"], 1, "11,12", "Social Studies"),
    ("AP Comparative Government & Politics", ["HS2205"], 1, "11,12", "Social Studies"),
    # SCIENCE
    ("Physics-Chemistry Lab Science", ["HS4007"], 1, "9", "Science"),
    ("Biology Lab Science", ["HS4008"], 1, "10", "Science"),
    ("Chemistry", ["HS4004"], 1, "11,12", "Science"),
    ("Earth & Space Science", ["HS4029"], 1, "11,12", "Science"),
    ("IB Environmental Systems & Society SL Y1-Y2", ["HS4115", "HS4125"], 1, "11,12", "Science"),
    ("IB Sports, Exercise & Health Science SL Y1-Y2", ["HS7030", "HS7031"], 1, "11,12", "Science"),
    ("IB Sports, Exercise & Health Science HL Y1-Y2", ["HS7050", "HS7051"], 1, "11,12", "Science"),
    ("IB Biology SL Y1-Y2", ["HS4110", "HS4120"], 2, "11,12", "Science"),
    ("IB Biology HL Y1-Y2", ["HS4130", "HS4140"], 2, "11,12", "Science"),
    ("IB Chemistry SL Y1-Y2", ["HS4111", "HS4121"], 2, "11,12", "Science"),
    ("IB Chemistry HL Y1-Y2", ["HS4131", "HS4141"], 2, "11,12", "Science"),
    ("IB Physics SL Y1-Y2", ["HS4112", "HS4122"], 2, "11,12", "Science"),
    ("IB Physics HL Y1-Y2", ["HS4132", "HS4142"], 2, "11,12", "Science"),
    ("AP Biology", ["HS4200"], 1, "11,12", "Science"),
    ("AP Chemistry", ["HS4201"], 1, "11,12", "Science"),
    ("AP Physics 1", ["HS4210"], 1, "11,12", "Science"),
    ("AP Physics C: Mechanics", ["HS4208"], 1, "11,12", "Science"),
    ("AP Physics C: Electricity & Magnetism", ["HS4209"], 1, "11,12", "Science"),
    # GLOBAL LANGUAGES
    ("Accelerated Beginner French", ["HS5054"], 1, "9,10,11,12", "Global Languages"),
    ("Intermediate French", ["HS5055"], 1, "10,11,12", "Global Languages"),
    ("Intermediate Low French", ["HS5056"], 1, "9,10,11,12", "Global Languages"),
    ("Intermediate High French", ["HS5057"], 1, "10,11,12", "Global Languages"),
    ("IB French B SL Y1-Y2", ["HS5110", "HS5120"], 2, "11,12", "Global Languages"),
    ("IB French B HL Y1-Y2", ["HS5130", "HS5140"], 2, "11,12", "Global Languages"),
    ("IB French Ab Initio SL Y1-Y2", ["HS5151", "HS5152"], 2, "11,12", "Global Languages"),
    ("Accelerated Beginner Spanish", ["HS5058"], 1, "9,10,11,12", "Global Languages"),
    ("Intermediate Spanish", ["HS5059"], 1, "9,10,11,12", "Global Languages"),
    ("Intermediate Low Spanish", ["HS5060"], 1, "9,10,11,12", "Global Languages"),
    ("Intermediate High Spanish", ["HS5061"], 1, "9,10,11,12", "Global Languages"),
    ("IB Spanish B SL Y1-Y2", ["HS5111", "HS5121"], 2, "11,12", "Global Languages"),
    ("IB Spanish B HL Y1-Y2", ["HS5131", "HS5141"], 2, "11,12", "Global Languages"),
    ("IB Spanish Ab Initio SL Y1-Y2", ["HS5155", "HS5156"], 2, "11,12", "Global Languages"),
    ("IB Self-Taught Language A1 SL Y1-Y2", ["HS5102", "HS5103"], 2, "11,12", "Global Languages"),
    # CHINESE LANGUAGE
    ("Novice Chinese", ["HS5024"], 1, "9,10,11,12", "Chinese Language"),
    ("Intermediate Low", ["HS5025"], 1, "9,10,11,12", "Chinese Language"),
    ("Intermediate Mid", ["HS5026"], 1, "9,10,11,12", "Chinese Language"),
    ("Intermediate High", ["HS3033"], 1, "9,10,11,12", "Chinese Language"),
    ("Advanced Low", ["HS5031"], 1, "9,10,11,12", "Chinese Language"),
    ("Advanced Mid", ["HS5032"], 1, "9,10,11,12", "Chinese Language"),
    ("Advanced High", ["HS3034"], 1, "9,10,11,12", "Chinese Language"),
    ("Superior", ["HS5147"], 1, "9,10,11,12", "Chinese Language"),
    ("IB Mandarin Ab Initio SL", ["HS5159", "HS5150"], 2, "11,12", "Chinese Language"),
    ("IB Mandarin B SL Y1-Y2", ["HS5113", "HS5123"], 2, "11,12", "Chinese Language"),
    ("IB Mandarin B HL Y1-Y2", ["HS5133", "HS5143"], 2, "11,12", "Chinese Language"),
    ("IB Chinese A: Language & Literature SL Y1-Y2", ["HS5114", "HS5124"], 2, "11,12", "Chinese Language"),
    ("IB Chinese A: Language & Literature HL Y1-Y2", ["HS5134", "HS5144"], 2, "11,12", "Chinese Language"),
    # VISUAL ARTS
    ("Art Lab", ["HS6064"], 1, "9,10,11,12", "Visual Arts"),
    ("Intermediate Art Studio", ["HS6207"], 1, "10,11,12", "Visual Arts"),
    ("Advanced Art Studio", ["HS6208"], 1, "11,12", "Visual Arts"),
    ("IB Visual Art SL Y1-Y2", ["HS6110", "HS6120"], 2, "11,12", "Visual Arts"),
    ("IB Visual Art HL Y1-Y2", ["HS6130", "HS6140"], 2, "11,12", "Visual Arts"),
    ("IB Film SL Y1-Y2", ["HS8165", "HS8175"], 2, "11,12", "Visual Arts"),
    ("Intro to Digital Filmmaking", ["HS8001"], 1, "9,10,11,12", "Visual Arts"),
    ("Design Theory", ["HS8506"], 1, "9,10,11,12", "Visual Arts"),
    # PERFORMING ARTS
    ("Concert Choir 1", ["HS6020"], 1, "9,10,11,12", "Performing Arts"),
    ("Concert Choir 2", ["HS6021"], 1, "9,10,11,12", "Performing Arts"),
    ("Concert Band 1", ["HS6022"], 1, "9,10,11,12", "Performing Arts"),
    ("Concert Band 2", ["HS6023"], 1, "9,10,11,12", "Performing Arts"),
    ("Orchestra", ["HS6019"], 1, "9,10,11,12", "Performing Arts"),
    ("Music Production 1", ["HS7016"], 1, "9,10,11,12", "Performing Arts"),
    ("Music Production 2", ["HS7017"], 1, "10,11,12", "Performing Arts"),
    ("Guitar 1", ["HS6026"], 1, "9,10,11,12", "Performing Arts"),
    ("Guitar 2", ["HS6027"], 1, "9,10,11,12", "Performing Arts"),
    ("IB Music SL Y1-Y2", ["HS6111", "HS6121"], 2, "11,12", "Performing Arts"),
    ("IB Music HL Y1-Y2", ["HS6131", "HS6141"], 2, "11,12", "Performing Arts"),
    ("Theatre Performance", ["HS6029"], 0.5, "9,10,11,12", "Performing Arts"),
    ("Theatre Production Design", ["HS6030"], 0.5, "9,10,11,12", "Performing Arts"),
    ("Advanced Dance", ["HS7015"], 1, "9,10,11,12", "Performing Arts"),
    ("Dance 1-2", ["HS7010"], 0.5, "9,10,11,12", "Performing Arts"),
    ("IB Dance SL Y1-Y2", ["HS7013", "HS7023"], 1, "9,10,11,12", "Performing Arts"),
    ("IB Dance HL Y1-Y2", ["HS7043"], 1, "9,10,11,12", "Performing Arts"),
    ("IB Theatre SL Y1-Y2", ["HS6112", "HS6122"], 2, "11,12", "Performing Arts"),
    ("IB Theatre HL Y1-Y2", ["HS6132", "HS6142"], 2, "11,12", "Performing Arts"),
    # APPLIED ARTS
    ("Fundamentals of Physical Computing", ["HS7018"], 0.5, "9,10,11,12", "Applied Arts"),
    ("Fundamentals of Robotics", ["HS8011"], 0.5, "9,10,11,12", "Applied Arts"),
    ("Advanced Physical Computing", ["HS7028"], 1, "9,10,11,12", "Applied Arts"),
    ("Fundamentals of Web Design", ["HS8006"], 0.5, "9,10,11,12", "Applied Arts"),
    ("Fundamentals of Applied Engineering", ["HS8006"], 0.5, "9,10,11,12", "Applied Arts"),
    ("Fundamentals of Coding for STEAM (Control Systems)", ["HS8006"], 0.5, "9,10,11,12", "Applied Arts"),
    ("Fundamentals of Game Development", ["HS8006"], 0.5, "9,10,11,12", "Applied Arts"),
    ("STEM-GTAE Gateway", ["HS8006"], 1, "9,10,11,12", "Applied Arts"),
    # GTAE PATHWAY
    ("Introduction to Robotics (Robotics & Automation)", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Product Design & Manufacturing", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Physical Computing", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Python Programming for Engineers", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Applied Engineering", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Introduction to Design Theory", ["HS0009"], 0.25, "9,10,11,12", "GTAE Pathway"),
    ("Engineering Capstone", ["HS8406"], 1, "9,10,11,12", "GTAE Pathway"),
    # PHYSICAL AND HEALTH EDUCATION
    ("Physical & Health Education 1", ["HS7000"], 1, "9", "Physical and Health Education"),
    ("Physical & Health Education 2", ["HS7001"], 1, "10", "Physical and Health Education"),
    ("PE 3 - Personal Fitness", ["HS7002"], 0.5, "11,12", "Physical and Health Education"),
    ("PE 3 - Swimming & Water Safety Instructor", ["HS7006"], 0.5, "11,12", "Physical and Health Education"),
    ("PE 3 - Lifeguarding", ["HS7007"], 0.5, "11,12", "Physical and Health Education"),
    # ELECTIVE COURSES
    ("Theory of Knowledge Y1-Y2", ["HS8101", "HS8102"], 1, "11,12", "Elective Courses"),
    ("AP Research", ["HS8400"], 1, "11,12", "Elective Courses"),
    ("AP Computer Science Principles: Python", ["HS8204"], 1, "11,12", "Elective Courses"),
    ("AP Computer Science A", ["HS8201"], 1, "11,12", "Elective Courses"),
    ("IB Computer Science SL Y1-Y2", ["HS8115", "HS8125"], 2, "11,12", "Elective Courses"),
    ("IB Computer Science HL Y1-Y2", ["HS8135", "HS8145"], 2, "11,12", "Elective Courses"),
    ("IB Sports, Exercise, & Health Science SL/HL Y1-Y2", ["HS7050", "HS7051"], 1, "11,12", "Elective Courses"),
    ("Independent Study", ["HS8405"], 1, "11,12", "Elective Courses"),
    # LEARNING SUPPORT
    ("Learning Support", ["HS8901"], 0, "9,10,11,12", "Learning Support"),
    # ONLINE LEARNING
    ("Pamoja Education", ["HS0"], None, "11,12", "Online Learning"),
    ("Virtual High School", ["HS9100"], None, "11,12", "Online Learning"),
    ("Global Online Academy", ["HS9103"], None, "11,12", "Online Learning"),
]


def extract_text_by_page(pdf_path: str) -> list[str]:
    """Extract text from each page of a PDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return pages


def clean_page_text(text: str) -> str:
    """Remove header/footer noise from extracted page text."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip common header/footer patterns
        if re.match(r'^2\s*0\s*2\s*[56]\s*-\s*2\s*0\s*2\s*[67]', stripped):
            continue
        if re.match(r'^H\s*I\s*G\s*H\s+S\s*C\s*H\s*O\s*O\s*L', stripped):
            continue
        if re.match(r'^C\s*O\s*U\s*R\s*S\s*E\s+C\s*A\s*T\s*A\s*L\s*O\s*G', stripped):
            continue
        if re.match(r'^PUDONG|^PUXI|^Shanghai American School', stripped):
            continue
        if re.match(r'^P\s*U\s*D\s*O\s*N\s*G|^P\s*U\s*X\s*I', stripped):
            continue
        if re.match(r'^\d+$', stripped) and len(stripped) <= 3:
            continue  # page numbers
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_name(name: str) -> str:
    """Normalize a course name for matching."""
    n = name.lower().strip()
    # Remove Y1-Y2 / Year 1-2 suffixes
    n = re.sub(r'\s*y1[-–]y2\s*', '', n)
    n = re.sub(r'\s*year\s*1[-–]2\s*', '', n)
    # Normalize IB SL/HL patterns
    n = re.sub(r'\s*\(sl/hl\)\s*', ' ', n)
    n = re.sub(r'\s*\(sl\)\s*', ' sl ', n)
    n = re.sub(r'\s*\(hl\)\s*', ' hl ', n)
    n = re.sub(r'\s+sl\s*$', '', n)
    n = re.sub(r'\s+hl\s*$', '', n)
    # Normalize punctuation
    n = n.replace('&', 'and')
    n = n.replace('–', '-')
    n = n.replace("'", "'")
    n = re.sub(r'\s*:\s*', ': ', n)
    # Remove extra spaces
    n = re.sub(r'\s+', ' ', n).strip()
    # Remove trailing periods
    n = n.rstrip('.')
    return n


def normalize_name_aggressive(name: str) -> str:
    """More aggressive normalization for fuzzy matching."""
    n = normalize_name(name)
    # Remove all SL/HL markers entirely
    n = re.sub(r'\b(sl|hl)\b', '', n)
    # Remove common abbreviation differences
    n = n.replace('u.s.', 'us')
    n = n.replace('u. s.', 'us')
    # Remove parenthetical content
    n = re.sub(r'\([^)]*\)', '', n)
    # Remove 1, 2, 3 suffixes for "Advanced X 1, 2, 3" courses
    n = re.sub(r'\s*\d+\s*,\s*\d+\s*,\s*\d+\s*$', '', n)
    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def match_description_to_master(master_name: str, descriptions: dict) -> dict | None:
    """Multi-level fuzzy matching of a master list course name to parsed descriptions."""
    # Level 1: Exact match
    if master_name in descriptions:
        return descriptions[master_name]

    # Level 2: Case-insensitive
    mn_lower = master_name.lower().strip()
    for dname, ddata in descriptions.items():
        if dname.lower().strip() == mn_lower:
            return ddata

    # Level 3: Normalized match
    mn_norm = normalize_name(master_name)
    for dname, ddata in descriptions.items():
        if normalize_name(dname) == mn_norm:
            return ddata

    # Level 4: Aggressive normalized match
    mn_agg = normalize_name_aggressive(master_name)
    for dname, ddata in descriptions.items():
        if normalize_name_aggressive(dname) == mn_agg:
            return ddata

    # Level 5: Substring/contains matching for IB courses
    # IB courses in descriptions often use combined "SL/HL" format
    if master_name.startswith("IB "):
        # Strip SL/HL and Y1-Y2 from master name to get core name
        core = re.sub(r'\s*(SL|HL|SL/HL)\s*', ' ', master_name)
        core = re.sub(r'\s*Y1-Y2\s*', '', core).strip()
        core = re.sub(r'\s+', ' ', core)
        core_lower = core.lower()
        for dname, ddata in descriptions.items():
            dn_clean = re.sub(r'\s*(SL|HL|SL/HL|\(SL/HL\)|\(SL\)|\(HL\))\s*', ' ', dname)
            dn_clean = re.sub(r'\s*Y1-Y2\s*', '', dn_clean).strip()
            dn_clean = re.sub(r'\s+', ' ', dn_clean)
            if dn_clean.lower() == core_lower:
                return ddata

    # Level 6: Partial name match (beginning of name matches)
    mn_words = normalize_name(master_name).split()
    if len(mn_words) >= 3:
        mn_prefix = " ".join(mn_words[:3])
        for dname, ddata in descriptions.items():
            dn_words = normalize_name(dname).split()
            if len(dn_words) >= 3 and " ".join(dn_words[:3]) == mn_prefix:
                return ddata

    return None


def build_course_record(name, codes, credits, grades, department, campus):
    """Build a single course record dict."""
    course_type = "SAS"
    if name.startswith("AP "):
        course_type = "AP"
    elif name.startswith("IB "):
        course_type = "IB"

    ib_level = None
    if course_type == "IB":
        if " HL " in name:
            ib_level = "HL"
        elif " SL " in name:
            ib_level = "SL"
        elif "SL/HL" in name:
            ib_level = "SL/HL"
        elif "Ab Initio" in name:
            ib_level = "SL"

    grade_list = []
    if grades:
        for g in grades.replace(" ", "").split(","):
            try:
                grade_list.append(int(g))
            except ValueError:
                pass

    return {
        "course_name": name,
        "course_codes": codes,
        "credits": credits,
        "grade_levels": grade_list,
        "grade_levels_display": grades,
        "department": department,
        "course_type": course_type,
        "ib_level": ib_level,
        "campus": campus,
        "school_year": "2026-2027",
        "school": "Shanghai American School",
        "prerequisites": None,
        "course_description": None,
        "main_topics": [],
        "learning_outcomes": [],
    }


def extract_descriptions_from_pages(pages_text: list[str], start_page: int, end_page: int) -> dict:
    """
    Extract course descriptions from a range of pages.
    Returns dict keyed by course name -> description data.
    """
    # Clean each page and join
    cleaned_pages = [clean_page_text(p) for p in pages_text[start_page:end_page]]
    text = "\n".join(cleaned_pages)

    results = {}

    # Primary pattern: Course name line followed by Prerequisites and Grade Levels
    # NOTE: Use [ \t]* (not \s*) before \n to avoid matching across newlines
    # Use greedy + (not +?) for course name to consume full line
    course_pattern = re.compile(
        r'^([A-Z][A-Za-z0-9&:,/\-\+\(\) \'\.]+)[ \t]*\n'
        r'(?:Course Code[s]?:?[ \t]*[^\n]*\n)?'
        r'(?:Duration:?[ \t]*[^\n]*\n)?'
        r'Prerequisite[s]?:?[ \t]*([^\n]*)\n'
        r'Grade [Ll]evel[s]?[ \t]*:?[ \t]*([^\n]*)\n',
        re.MULTILINE
    )

    # Fallback pattern: Grade Levels without Prerequisites line
    course_pattern2 = re.compile(
        r'^([A-Z][A-Za-z0-9&:,/\-\+\(\) \'\.]+)[ \t]*\n'
        r'(?:Course Code[s]?:?[ \t]*[^\n]*\n)?'
        r'(?:Duration:?[ \t]*[^\n]*\n)?'
        r'Grade [Ll]evel[s]?[ \t]*:?[ \t]*([^\n]*)\n',
        re.MULTILINE
    )

    # Collect all matches from both patterns
    all_matches = []
    seen_positions = set()

    for m in course_pattern.finditer(text):
        all_matches.append((m.start(), m.end(), m.group(1).strip(),
                            m.group(2).strip() if m.group(2) else None,
                            m.group(3).strip() if m.group(3) else None))
        seen_positions.add(m.start())

    for m in course_pattern2.finditer(text):
        if m.start() not in seen_positions:
            all_matches.append((m.start(), m.end(), m.group(1).strip(),
                                None,
                                m.group(2).strip() if m.group(2) else None))

    # Sort by position in text
    all_matches.sort(key=lambda x: x[0])

    for i, (mstart, mend, name, prereq, grade_text) in enumerate(all_matches):
        # Skip false positives (very short names, or names that are section headers)
        if len(name) < 4:
            continue
        if name in ("English", "Mathematics", "Social Studies", "Science",
                     "Visual Arts", "Performing Arts", "Applied Arts",
                     "Chinese Language", "Global Languages", "GTAE Pathway",
                     "Physical and Health Education", "Other Courses"):
            continue

        # Find end of this course entry
        start = mend
        end = all_matches[i + 1][0] if i + 1 < len(all_matches) else len(text)
        block = text[start:end].strip()

        desc, topics, outcomes = _parse_description_block(block)

        # Only store if we got meaningful content
        if desc or topics or outcomes:
            results[name] = {
                "prerequisites": prereq,
                "course_description": desc,
                "main_topics": topics[:15],
                "learning_outcomes": outcomes[:15],
            }

    return results


def _parse_description_block(block: str) -> tuple[str, list, list]:
    """Parse a course description block into description, topics, and outcomes."""
    desc = ""
    topics = []
    outcomes = []

    # Split by Main Topics and Learning Outcomes
    parts = re.split(r'\n(?:Main Topics:?|Main topics:?)\s*\n', block, maxsplit=1)
    if len(parts) >= 2:
        desc = parts[0]
        remainder = parts[1]

        topic_parts = re.split(r'\n(?:Learning Outcomes:?|Learning outcomes:?)\s*\n', remainder, maxsplit=1)
        topics = _parse_bullet_list(topic_parts[0])

        if len(topic_parts) >= 2:
            outcomes = _parse_bullet_list(topic_parts[1])
    else:
        # Try alternative split patterns
        parts = re.split(r'\nMain Topics\n', block, maxsplit=1)
        if len(parts) >= 2:
            desc = parts[0]
            topic_parts = re.split(r'\nLearning Outcomes\n', parts[1], maxsplit=1)
            topics = _parse_bullet_list(topic_parts[0])
            if len(topic_parts) >= 2:
                outcomes = _parse_bullet_list(topic_parts[1])
        else:
            desc = block

    # Clean description
    desc = re.sub(r'^Course Description\s*\n?', '', desc).strip()
    desc = re.sub(r'^Credits?:?\s*[\d\.]+\s*\n?', '', desc).strip()
    # Remove any remaining header noise
    desc = re.sub(r'2\s*0\s*2\s*[56]\s*-\s*2\s*0\s*2\s*[67].*?CATALOG', '', desc, flags=re.IGNORECASE)
    desc = desc.strip()

    if len(desc) > 2000:
        desc = desc[:2000] + "..."

    return desc, topics, outcomes


def _parse_bullet_list(text: str) -> list[str]:
    """Parse bullet-pointed text into a list of items."""
    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Remove bullet characters
        cleaned = stripped.lstrip("•·–-▪▸►◦∙").strip()
        if len(cleaned) < 4:
            continue
        # Skip noise lines
        if re.match(r'^2\s*0\s*2\s*[56]', cleaned):
            continue
        if re.match(r'^(Main|Learning|Course|Prerequisites|Grade)', cleaned):
            continue
        items.append(cleaned)
    return items


def cross_copy_descriptions(all_courses: list[dict]):
    """Copy descriptions from PDHS courses to matching PXHS courses that lack descriptions."""
    # Build lookup from PDHS courses that have descriptions
    pdhs_descs = {}
    for c in all_courses:
        if c["campus"] == "PDHS" and c["course_description"]:
            key = normalize_name_aggressive(c["course_name"])
            pdhs_descs[key] = {
                "prerequisites": c["prerequisites"],
                "course_description": c["course_description"],
                "main_topics": c["main_topics"],
                "learning_outcomes": c["learning_outcomes"],
            }

    copied = 0
    for c in all_courses:
        if c["campus"] == "PXHS" and not c["course_description"]:
            key = normalize_name_aggressive(c["course_name"])
            if key in pdhs_descs:
                c["prerequisites"] = pdhs_descs[key]["prerequisites"]
                c["course_description"] = pdhs_descs[key]["course_description"]
                c["main_topics"] = pdhs_descs[key]["main_topics"]
                c["learning_outcomes"] = pdhs_descs[key]["learning_outcomes"]
                copied += 1

    return copied


def main():
    base_dir = Path(__file__).parent.parent
    pdhs_path = base_dir / "data/input/pdfs/division catalogs/670PDHS Course Catalog 2026-27.pdf"
    pxhs_path = base_dir / "data/input/pdfs/division catalogs/PXHS_Course_Catalog_2026-27.pdf"
    output_dir = base_dir / "data/output/json"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_courses = []

    for campus_name, pdf_path, master_list in [
        ("PDHS", pdhs_path, PDHS_MASTER),
        ("PXHS", pxhs_path, PXHS_MASTER),
    ]:
        print(f"\n{'='*60}")
        print(f"Processing {campus_name}: {pdf_path.name}")
        print(f"{'='*60}")

        # Extract text from all pages
        pages = extract_text_by_page(str(pdf_path))
        total_chars = sum(len(p) for p in pages)
        print(f"  Extracted text from {len(pages)} pages ({total_chars:,} chars)")

        # Extract course descriptions from description pages
        # PDHS descriptions: pages 12-66 (0-indexed: 11-66)
        # PXHS descriptions: pages 15-62 (0-indexed: 14-62) - NOTE: image-based, will be empty
        if campus_name == "PDHS":
            desc_start, desc_end = 11, len(pages)
        else:
            desc_start, desc_end = 14, len(pages)

        descriptions = extract_descriptions_from_pages(pages, desc_start, desc_end)
        print(f"  Parsed {len(descriptions)} course descriptions from text")

        # Build course records from master list
        campus_courses = []
        matched = 0
        unmatched = []
        for name, codes, credits, grades, dept in master_list:
            record = build_course_record(name, codes, credits, grades, dept, campus_name)

            desc_data = match_description_to_master(name, descriptions)
            if desc_data:
                record["prerequisites"] = desc_data["prerequisites"]
                record["course_description"] = desc_data["course_description"]
                record["main_topics"] = desc_data["main_topics"]
                record["learning_outcomes"] = desc_data["learning_outcomes"]
                matched += 1
            else:
                unmatched.append(name)

            campus_courses.append(record)

        print(f"  {len(campus_courses)} courses from master list")
        print(f"  {matched} matched with descriptions ({len(unmatched)} without)")

        if unmatched and len(descriptions) > 0:
            print(f"  Unmatched courses:")
            for n in unmatched[:15]:
                print(f"    - {n}")

        # Report parsed descriptions that didn't match any master list course
        matched_desc_names = set()
        for name, *_ in master_list:
            if match_description_to_master(name, descriptions):
                d = match_description_to_master(name, descriptions)
                for dname, ddata in descriptions.items():
                    if ddata is d:
                        matched_desc_names.add(dname)
                        break
        extra_descs = [n for n in descriptions if n not in matched_desc_names]
        if extra_descs:
            print(f"  {len(extra_descs)} parsed descriptions not matched to any master list entry:")
            for n in extra_descs[:10]:
                print(f"    + {n}")

        all_courses.extend(campus_courses)

    # Cross-copy descriptions from PDHS to PXHS for shared courses
    copied = cross_copy_descriptions(all_courses)
    print(f"\n  Cross-copied {copied} descriptions from PDHS to PXHS")

    # Final coverage
    pdhs_with_desc = sum(1 for c in all_courses if c["campus"] == "PDHS" and c["course_description"])
    pxhs_with_desc = sum(1 for c in all_courses if c["campus"] == "PXHS" and c["course_description"])
    pdhs_total = sum(1 for c in all_courses if c["campus"] == "PDHS")
    pxhs_total = sum(1 for c in all_courses if c["campus"] == "PXHS")

    # Output
    output_file = output_dir / "sas_course_catalogs_2026-27.json"
    output = {
        "metadata": {
            "school": "Shanghai American School",
            "school_year": "2026-2027",
            "campuses": ["PDHS", "PXHS"],
            "extraction_date": "2026-02-28",
            "total_courses": len(all_courses),
            "pdhs_courses": pdhs_total,
            "pxhs_courses": pxhs_total,
            "description_coverage": {
                "pdhs": f"{pdhs_with_desc}/{pdhs_total}",
                "pxhs": f"{pxhs_with_desc}/{pxhs_total} ({copied} cross-copied from PDHS)",
                "total": f"{pdhs_with_desc + pxhs_with_desc}/{len(all_courses)}",
            },
        },
        "courses": all_courses,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Output: {output_file}")
    print(f"Total courses: {len(all_courses)}")
    print(f"  PDHS: {pdhs_total} ({pdhs_with_desc} with descriptions)")
    print(f"  PXHS: {pxhs_total} ({pxhs_with_desc} with descriptions, {copied} cross-copied)")
    print(f"  Overall coverage: {pdhs_with_desc + pxhs_with_desc}/{len(all_courses)} "
          f"({100*(pdhs_with_desc + pxhs_with_desc)/len(all_courses):.0f}%)")

    # Report remaining courses without descriptions
    missing = [c for c in all_courses if not c["course_description"]]
    if missing:
        print(f"\n  Courses still missing descriptions ({len(missing)}):")
        for c in missing:
            print(f"    [{c['campus']}] {c['course_name']}")


if __name__ == "__main__":
    main()
