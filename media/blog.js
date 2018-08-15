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

function coarse_line(startx, starty, endx, endy, coarseness, segments = 2){
  // 画一条比较粗糙的线条, 具有类似手绘的感觉.
  // coarseness是曲线的不规则程度, segments是用几段曲线来画.
  var x, y, choice, nextx, nexty, dx1, dx2, dy1, dy2, l, lastx, lasty, desc;
  var desc = `M ${startx} ${starty}, `;

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
    desc += ` C${(2*lastx+nextx)/3+dx1} ${(2*lasty+nexty)/3+dy1}, ${(lastx+2*nextx)/3+dx2} ${(lasty+2*nexty)/3+dy2}, ${nextx} ${nexty}`;
    lastx = nextx;
    lasty = nexty;
  }
  return desc
}

function writeK(){
  var svg_size = document.getElementById('logo-svg').clientWidth;
  var half = svg_size * 0.5;
  var width = svg_size * 0.02;
  var radius = svg_size * 0.42;

  var path1_x = svg_size * 0.29;
  var path1_y = svg_size * 0.21;
  var path1_x_end = svg_size * 0.29;
  var path1_y_end = svg_size * 0.79;

  var path2_x = svg_size * 0.29;
  var path2_y = svg_size * 0.57;
  var path2_x_end = svg_size * 0.70;
  var path2_y_end = svg_size * 0.21;

  var path3_x = svg_size * 0.44;
  var path3_y = svg_size * 0.44;
  var path3_x_end = svg_size * 0.71;
  var path3_y_end = svg_size * 0.79;

  document.getElementById("svg-circle").setAttribute("cx", half);
  document.getElementById("svg-circle").setAttribute("cy", half);
  document.getElementById("svg-circle").setAttribute("r", radius);

  document.getElementById("svg-path1").setAttribute("stroke-width", width);
  document.getElementById("svg-path2").setAttribute("stroke-width", width);
  document.getElementById("svg-path3").setAttribute("stroke-width", width);

  document.getElementById("svg-path1").setAttribute("d", coarse_line(path1_x, path1_y, path1_x_end, path1_y_end, 1));
  document.getElementById("svg-path2").setAttribute("d", coarse_line(path2_x, path2_y, path2_x_end, path2_y_end, 5));
  document.getElementById("svg-path3").setAttribute("d", coarse_line(path3_x, path3_y, path3_x_end, path3_y_end, 3));
}

//       __
// |__| |  | |__|
//    | |__|    |
//
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
