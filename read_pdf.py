import PyPDF2

def read_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'
        with open('output.txt', 'w', encoding='utf-8') as out_file:
            out_file.write(text)

read_pdf('İleri Veritabanı Proje Dokumani.pdf')
