import pandas
import requests


# FUNCTIONS
def get_json_from_openlibrary(query):
    response = requests.get(url=f"https://openlibrary.org/{query}.json")
    if response.status_code != 200:
        return False
    json_data = response.json()
    return json_data


def get_author_names(json_data, row):
    if not json_data:
        if isinstance(row['Citation Author'], str):
            if len(row['Citation Author']) > 0:
                return [row['Citation Author']]
            else:
                return ["[no author]"]
        else:
            return ["[no author]"]
    author_names = []
    if "authors" in json_data.keys():
        for author in json_data['authors']:
            author_json = get_json_from_openlibrary(author['key'])
            if "name" in author_json.keys():
                author_names.append(author_json["name"])
            elif "personal_name" in author_json.keys():
                author_names.append(author_json["personal_name"])
            else:
                author_names.append("[no author]")
        return author_names
    else:
        if isinstance(row['Citation Author'], str):
            if len(row['Citation Author']) > 0:
                return [row['Citation Author']]
            else:
                return ["[no author]"]
        else:
            return ["[no author]"]


def format_author_string(author_list):
    skip = False
    if author_list[0] == "[no author]":
        return ""
    elif "edited by" in author_list[0]:
        formatted_first_author = f"({author_list[0]})"
        skip = True
    elif "ed." in author_list[0] or "trans." in author_list[0]:
        formatted_first_author = author_list[0]
    elif "," in author_list[0]:
        formatted_first_author = author_list[0]
        skip = True
    if not skip:
        edited_first_author = remove_digits(author_list[0])
        first_author_names = edited_first_author.split()
        if "author" in first_author_names:
            first_author_names.remove("author")
        first_author_names.insert(0, first_author_names.pop(-1))
        for name in first_author_names:
            if name == first_author_names[0]:
                if len(first_author_names) == 0:
                    formatted_first_author = f"{name}"
                else:
                    formatted_first_author = f"{name},"
            else:
                formatted_first_author += f" {name}"
    author_string = formatted_first_author
    if len(author_list) == 0:
        return author_string
    elif len(author_list) > 3:
        return author_string + " et al."
    else:
        for author in author_list[1:]:
            if author == author_list[-1]:
                author_string += f" and {author}"
            else:
                author_string += f", {author}"
        return author_string


def get_publisher(json_data):
    if "publishers" in json_data.keys():
        publisher = json_data["publishers"][0]
    else:
        publisher = "[no publisher]"
    return publisher


def remove_statement_of_responsibility(title_string):
    x = title_string.find("/")
    return title_string[:x].strip()


def remove_digits(string):
    digits = "0123456789.-"
    no_digits = ""
    for char in string:
        if char not in digits:
            no_digits += char
    return no_digits


def remove_punctuation(string):
    punctuation = '''!()-[]{};:'’‘"\;,<>./?@#$%^&*_~'''
    no_punc = ""
    for char in string:
        if char not in punctuation:
            no_punc += char
    return no_punc


def check_if_statement_of_res(title_string):
    if "/" in title_string:
        return True
    else:
        return False


def format_title(string):
    title_proper = remove_statement_of_responsibility(string)
    formatted_title_proper = remove_punctuation(title_proper).lower().strip()
    split_string = formatted_title_proper.split()
    new_string = " ".join(split_string)
    return new_string


def get_notes_and_tags_html(row):
    notes_and_tags_html = ""
    if isinstance(row['Citation Public note'], str):
        notes_and_tags_html += f'"{row["Citation Public note"]}"<br>'
    if isinstance(row['Citation Tags'], str):
        notes_and_tags_html += "<span style='color: grey'><em>"
        split_tags = row['Citation Tags'].split(", ")
        for tag in split_tags:
            tag.replace(" ", "_")
            notes_and_tags_html += f"#{tag} "
        notes_and_tags_html += "</em></span><br>"
    return notes_and_tags_html


# CREATE HTML
with open("results.html", "w", encoding="utf-8") as file:
    file.write('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Autocheck results</title>
</head>
<body>''')

# READ CSVs
leganto_list_data = pandas.read_csv("english_i4.csv")
queens_library_data = pandas.read_csv("library_holdings.csv", encoding="utf-8")

# CREATE TABLE OF CONTENTS
html_contents = "<h3 id='top'>Contents:</h3><ul>"
sections = leganto_list_data['Section Name'].unique()
for i in range(len(sections)):
    html_contents += f"<li><a href='#{i + 1}'>{sections[i]}</a></li>"
html_contents += "</ul>"
with open("results.html", "a", encoding="utf-8") as file:
    file.write(html_contents)

counter = 1
sections = []
current_section = ""
for index, row in leganto_list_data.iterrows():
    print(f"Checking item {counter} of {len(leganto_list_data.index)}")
    counter += 1
    bib_data = {}
    print(f"TITLE: {row['Citation Title']}")
    # STRUCTURE INTO SECTIONS
    html_section = ""
    if row["Section Name"] != current_section:
        sections.append(row["Section Name"])
        current_section = row["Section Name"]
        html_section += f"<h2 style='display: inline-block' id='{len(sections)}'>{row['Section Name']}</h2> [<a href='#top'>back to top</a>]"
    # STEP 1: CHECK IF THIS IS A BOOK
    if row["Citation Type"] in ["Book", "Book Chapter", "Book Extract", "E-book"]:
        ol_book_data = get_json_from_openlibrary("isbn/" + str(row["Citation ISBN"]))
        # STEP 2: DOES QUEENS' HAVE A HOLDINGS RECORD ATTACHED?
        if "Queens'" in str(row["Citation Availability"]):
            bib_data["match"] = "Library's holdings are attached."
            bib_data["colour"] = "MediumSeaGreen"
            bib_data['match_info'] = ""
        # STEP 3: DOES THE ISBN MATCH QUEENS' ISBNs?
        if "match" not in bib_data.keys():
            leganto_ISBN = row["Citation ISBN"]
            library_ISBNs = []  # used in step 4
            for i, r in queens_library_data.iterrows():
                if isinstance(r["ISBN"], str):
                    library_ISBNs += r["ISBN"].split("; ")
                    if leganto_ISBN in r["ISBN"].split("; "):
                        bib_data["match"] = "ISBN matches library's holdings."
                        bib_data["colour"] = "MediumSeaGreen"
                        bib_data['match_info'] = ""
                        break
        # STEP 4: DO ANY OF THE OTHER OPEN LIBRARY EDITIONS MATCH QUEENS' ISBNs?
        if "match" not in bib_data.keys():
            if ol_book_data is not False:
                if "works" in ol_book_data.keys():
                    work_ID = ol_book_data["works"][0]["key"]
                    ol_work_data = get_json_from_openlibrary(work_ID + "/editions")
                    for edition in ol_work_data["entries"]:
                        if "isbn_13" in edition.keys():
                            for edition_ISBN in edition['isbn_13']:
                                if int(edition_ISBN) in library_ISBNs:
                                    bib_data["match"] = "work"
                                    bib_data["colour"] = "LightGreen"
                                    bib_data[
                                        'match_info'] = f"Library has {edition['publishers'][0]}, {edition['publish_date']} edition."
                                    break
        # STEP 5: ARE THERE ANY TEXT MATCHES FOR AUTHORS/TITLES AMONG QUEENS' HOLDINGS?
        if "match" not in bib_data.keys():
            matches = []
            leganto_title = format_title(row["Citation Title"])
            for i, r in queens_library_data.iterrows():
                queens_title = format_title(r["Title"])
                if leganto_title in queens_title:
                    matches.append({
                        "MMSID": r["MMS Id"],
                        "location": r["Location Name"],
                        "classmark": r["Permanent Call Number"],
                        "statement of res": r["245$c"],
                        "title": r["Title"],
                        "publisher": r["Publisher"],
                        "date": r["Publication Date"]
                    })
                    bib_data["match"] = "Matches for this title are found among library holdings:"
                    bib_data["colour"] = "Orange"
                    bib_data["notes and tags"] = get_notes_and_tags_html(row)
                    if len(matches) > 7:
                        bib_data["match"] = "This title matched with too many library titles to be accurate."
                        bib_data["colour"] = "Orange"
                        bib_data["match_info"] = ""
                        break
            if 0 < len(matches) < 8:
                bib_data["match_info"] = "<ul>"
                for match in matches:
                    bib_data["match_info"] += f'''
    <li><strong>{match['location']}: {match['classmark']}</strong> {match['title']} {match['statement of res']}<br>
    —{match["publisher"]}, {match['date']} [MMSID: {match['MMSID']}]</li>
    '''
                bib_data["match_info"] += "</ul>"
        # STEP 6: REMAINING ITEMS WITH NO MATCHES
        if "match" not in bib_data.keys():
            bib_data["match"] = "No match found."
            bib_data["colour"] = "OrangeRed"
            bib_data['match_info'] = ""
            bib_data["notes and tags"] = get_notes_and_tags_html(row)
        # BOOK HTML FORMATTING
        html_chapter_author = ""
        if isinstance(row["Citation Chapter Author"], str):
            html_chapter_author = f"{row['Citation Chapter Author'].replace('author', '')}, "
        html_chapter = ""
        if row["Citation Type"] == "Book Chapter":
            html_chapter = f"'{row['Citation Chapter Title']}' in:<br>"
        author_string = format_author_string(get_author_names(ol_book_data, row))
        if author_string is None:
            author_string = ""
        if len(author_string) > 0:
            html_author = f"{author_string},"
        else:
            html_author = author_string
        if check_if_statement_of_res(row['Citation Title']):
            html_title = remove_statement_of_responsibility(row['Citation Title'])
        else:
            html_title = row['Citation Title']
        html_edition = ""
        if isinstance(row["Citation Edition"], str):
            html_edition += f"—{row['Citation Edition']}"
        html_pub = "—"
        if isinstance(row["Citation Place of publication"], str):
            html_pub += f"{row['Citation Place of publication']} : "
        if isinstance(row["Citation Publisher"], str):
            html_pub += row["Citation Publisher"]
        if html_pub[-1] not in ["]", ".", "-"]:
            html_pub += f", {row['Citation Publication Date']}."
        if "notes and tags" not in bib_data.keys():
            bib_data["notes and tags"] = ""
        with open("results.html", "a", encoding="utf-8") as file:
            file.write(f'''
            {html_section}
        <p>{html_chapter_author}{html_chapter}
        <span style="color:{bib_data['colour']}"><strong>{html_author} <em>{html_title}</em></strong>
        <br>{html_edition}{html_pub}<br>
        </span>{bib_data["notes and tags"]}⮩{bib_data["match"]}<br>{bib_data["match_info"]}
        </p>
        ''')
    elif row['Citation Type'] == "Article":
        with open("results.html", "a", encoding="utf-8") as file:
            file.write(f'''
            {html_section}
        <p><strong><span style="color:DimGrey">{row['Citation Author']}, 
        "{row['Citation Title']}", <em>{row['Citation Journal Title']}</em>
         ({row['Citation Publication Date']})</span></strong> 
        </p>
        ''')
    else:  # NON-BOOK/ARTICLE ITEMS
        with open("results.html", "a", encoding="utf-8") as file:
            file.write(f'''
            {html_section}
        <p><strong>{row['Citation Type']}:</strong> <span style="color:DimGrey"><em>{row['Citation Title']}</em></span>
        </p>
        ''')

with open("results.html", "a", encoding="utf-8") as file:
    file.write('''
</body>
</html>
''')


# SORT CODE INTO FUNCTIONS
