function coarseLine(context, startx, starty, endx, endy, segments, width, coarseness, color){
  // 画一条比较粗糙的线条, 具有类似手绘的感觉.
  // context是基础. 接下来四个参数是起始点和终结点的坐标.
  // segments是用几段曲线来画. width是曲线线宽. coarseness是曲线的不规则程度.
  color = typeof(color) != 'undefined' ? color : 'white';
  context.lineCap = 'round';
  var x, y, choice, nextx, nexty, dx1, dx2, dy1, dy2, l, lastx, lasty;
  context.beginPath();
  context.lineWidth = width;
  context.moveTo(startx, starty);
  l = Math.sqrt((startx - endx)*(startx - endx) + (starty - endy)*(starty - endy))
  lastx = startx;
  lasty = starty;
  for(index=0; index < segments; index++){
  choice=Math.random();
  if (choice > 0.5){
    delta1=Math.floor(Math.random()*(2*coarseness+1)) - coarseness;
    delta2=-Math.floor(Math.random()*(2*coarseness+1)) + (coarseness);
  }else{
    delta1=-Math.floor(Math.random()*(2*coarseness+1)) + (coarseness);
    delta2=Math.floor(Math.random()*(2*coarseness+1)) - (coarseness);
  }
  dx1 = Math.round((endy-starty)*delta1/l);
  dx2 = Math.round((endy-starty)*delta2/l);
  dy1 = Math.round((endx-startx)*delta1/l);
  dy2 = Math.round((endx-startx)*delta2/l);
  nextx = Math.round((endx - startx) / segments) + lastx;
  nexty = Math.round((endy - starty) / segments) + lasty;
  context.bezierCurveTo((2*lastx+nextx)/3+dx1,(2*lasty+nexty)/3+dy1,(lastx+2*nextx)/3+dx2,(lasty+2*nexty)/3+dy2,nextx,nexty);
  lastx = nextx;
  lasty = nexty;
  }
  context.strokeStyle = color;
  context.stroke();
  context.closePath();
}
function drawLogo() {
  // 初始化
  var canvas = document.getElementById('logo');
  var context = canvas.getContext('2d');
  context.globalAlpha=0.0;
  context.fillRect(0, 0, 100, 100);
  context.globalAlpha=1.0;

  gradient = context.createRadialGradient(50,50,0,50,50,42);
  gradient.addColorStop(0, "#4467AD");
  gradient.addColorStop(1, "#203D76");

  context.beginPath();
  context.arc(50, 50, 42, 0, Math.PI*2, false);
  context.fillStyle = gradient;
  context.moveTo(100, 50);
  context.fill()
  context.closePath();
  coarseLine(context, 29, 21, 29, 79, 2, 3, 1, "white");
  coarseLine(context, 29, 57, 70, 21, 2, 3, 5, "white");
  coarseLine(context, 45, 45, 71, 79, 2, 3, 3, "white");
}

function draw_404() {
  var canvas = document.getElementById('canvas-404');
  var context = canvas.getContext('2d');
  var x, y;
  context.globalAlpha=0.0;
  context.fillRect(0, 0, 200, 500);
  context.globalAlpha=1.0;

  // 4 between 60 and 90
  coarseLine(context, r(30, 15), r(10, 5), 10, 60, 1, 3, 5, "black");
  coarseLine(context, 10, 60, 70, 60, 1, 3, 5, "black");
  coarseLine(context, r(60, 5), r(10, 5), r(60, 5), r(110, 5), 2, 3, 5, "black");

  // 0
  coarseLine(context, 110, 10, 110, 110, 2, 3, 3, "black");
  coarseLine(context, 160, 10, 160, 110, 2, 3, 3, "black");
  coarseLine(context, 110, 10, 160, 10, 1, 3, 5, "black");
  coarseLine(context, 110, 110, 160, 110, 1, 3, 5, "black");

  // 4
  coarseLine(context, r(215, 15), r(10, 5), 195, 60, 1, 3, 5, "black");
  coarseLine(context, 195, 60, 255, 60, 1, 3, 5, "black");
  coarseLine(context, r(245, 5), r(10, 5), r(245, 5), r(110, 5), 2, 3, 5, "black");
}

function r(x, dx) {
  return x + Math.floor((Math.random() * dx * 2) - dx);
}

//       __
// |__| |  | |__|
//    | |__|    |
//

function updateheight(){
  current = window.scrollY;
  document.getElementById("header").style.height = (100 - current) +  "px";
}

