package com.griffin.prismprobe;
import android.app.*;import android.content.*;import android.media.projection.*;import android.os.*;import android.widget.*;
public final class ProbeActivity extends Activity {
 public void onCreate(Bundle state){super.onCreate(state);Button button=new Button(this);button.setText("Start temporary screen-capture test (no audio)");button.setOnClickListener(v->{try{startActivityForResult(((MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE)).createScreenCaptureIntent(),7);}catch(Exception e){button.setText("Capture unavailable: "+e.getClass().getSimpleName());}});setContentView(button);button.requestFocus();}
 protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==7&&result==RESULT_OK&&data!=null){Intent service=new Intent(this,CaptureService.class).setAction("START").putExtra("result",result).putExtra("data",data);startForegroundService(service);finish();}else Toast.makeText(this,"Screen-capture permission was not granted",Toast.LENGTH_LONG).show();}
}
