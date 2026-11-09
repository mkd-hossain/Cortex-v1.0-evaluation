from pathlib import Path
from PIL import Image,ImageOps,ImageDraw

root=Path(__file__).resolve().parent/'dashboard-qa'
pages=sorted(root.glob('final-page-*.png'))
sheet=Image.new('RGB',(3*320,((len(pages)+2)//3)*470),'#dce3eb')
draw=ImageDraw.Draw(sheet)
for index,path in enumerate(pages):
    image=Image.open(path).convert('RGB')
    image.thumbnail((300,430))
    x=(index%3)*320+10;y=(index//3)*470+25
    sheet.paste(image,(x,y))
    draw.text((x,y-18),f'Page {index+1}',fill='black')
sheet.save(root/'final-contact.png')
