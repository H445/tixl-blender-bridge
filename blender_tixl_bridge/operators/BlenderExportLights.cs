#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Numerics;
using System.Runtime.InteropServices;
using System.Text.Json;
using T3.Core.DataTypes;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;
namespace PrismalLabs.BlenderExport;

/// <summary>Loads Blender-exported light manifests and optional keyed light channels for the active scene. Area sources are represented by calibrated TiXL point lights and can be reused with any export manifest.</summary>
[Guid("ed467242-caba-58ac-b8e9-69a494a93e39")]
public sealed class BlenderExportLights : Instance<BlenderExportLights>
{
    [Output(Guid="9b031ccc-0af3-56dc-9c83-3d1f971a84cd",DirtyFlagTrigger=DirtyFlagTrigger.Animated)] public readonly Slot<Command> Output=new();
    [Input(Guid="15864c39-8af3-501d-9be8-3e07898e1060")] public readonly InputSlot<Command> Command=new();
    [Input(Guid="e0a26c9d-fc85-59a7-88b5-1d1b0d8c5c3f")] public readonly InputSlot<string> WorldDirectory=new();
    [Input(Guid="fc6c833a-fcc3-506a-9808-f2f5e0d21c17")] public readonly InputSlot<int> WorldIndex=new();
    [Input(Guid="51c24b39-749f-5bba-8c24-3c8376e49112")] public readonly InputSlot<float> TimeSeconds=new();
    [Input(Guid="48ad955c-730a-5e12-866b-938588a436ea")] public readonly InputSlot<float> EnergyScale=new();
    [Input(Guid="a17e4d92-6c38-4f0b-b5d1-2e9a7c8f6043")] public readonly InputSlot<string> SceneNames=new();
    private readonly List<Light>[] _lights=new List<Light>[8];
    private string _directory=string.Empty;
    private string _sceneNamesValue=string.Empty;
    private string[] _sceneNames=["scene"];
    private bool _loaded;
    public BlenderExportLights() {Output.UpdateAction=Update;}
    private void Update(EvaluationContext context)
    {
        var directory=WorldDirectory.GetValue(context)??string.Empty;
        var requestedNames=SceneNames.GetValue(context)??string.Empty;
        if(!_loaded || directory!=_directory || requestedNames!=_sceneNamesValue)
        {
            // TiXL renders a paused frame when the project opens. Load every
            // world's lights there; never open a new manifest at a scene cut.
            // If transport was already running, keep the previous cache until
            // it pauses instead of performing file I/O on a playback frame.
            if(Math.Abs(context.Playback.PlaybackSpeed)<=0.001)
            {
                var names=requestedNames.Split(',',StringSplitOptions.RemoveEmptyEntries|StringSplitOptions.TrimEntries);
                if(names.Length==0)names=["scene"];
                if(names.Length>_lights.Length)
                    throw new InvalidOperationException("BlenderExportLights supports at most 8 scene indices; use separate instances for larger sets.");
                var loaded=new List<Light>[names.Length];
                for(var i=0;i<names.Length;i++) loaded[i]=Load(directory,names[i]);
                Array.Clear(_lights);
                Array.Copy(loaded,_lights,loaded.Length);
                _sceneNames=names;
                _directory=directory;
                _sceneNamesValue=requestedNames;
                _loaded=true;
            }
        }
        var world=Math.Clamp(WorldIndex.GetValue(context),0,_sceneNames.Length-1);
        var lights=_lights[world];
        var frame=TimeSeconds.GetValue(context)*60+1;
        var scale=EnergyScale.GetValue(context);
        var pushed=0;
        try
        {
            foreach(var light in lights??[])
            {
                var energy=light.Energy;var position=light.Position;var color=light.Color;
                if(light.Samples.Count>0)
                {
                    var lo=0;var hi=light.Samples.Count-1;
                    while(lo<hi) {var mid=(lo+hi+1)/2;if(light.Samples[mid].Frame<=frame)lo=mid;else hi=mid-1;}
                    var a=light.Samples[lo];var b=light.Samples[Math.Min(lo+1,light.Samples.Count-1)];
                    var u=Math.Clamp((frame-a.Frame)/Math.Max(1,b.Frame-a.Frame),0,1);
                    energy=a.Energy*(1-u)+b.Energy*u;position=Vector3.Lerp(a.Position,b.Position,u);color=Vector4.Lerp(a.Color,b.Color,u);
                }
                if(pushed==T3.Core.Rendering.PointLightStack.MaxPointLights)break;
                // TiXL Range is attenuation distance, not Blender's cutoff distance.
                // A moderate radius keeps the exported room fill legible without the
                // overexposure produced by treating Blender's cutoff as a TiXL range.
                if(context.PointLights.Push(new T3.Core.Rendering.PointLight(position,energy*scale,color,1.5f,2)))pushed++;
            }
            Command.GetValue(context);
        }
        finally {for(int i=0;i<pushed;i++)context.PointLights.Pop();}
    }
    private static List<Light> Load(string directory,string world)
    {
        var result=new List<Light>();
        using(var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,world+"_manifest.json"))))
        {
            foreach(var item in doc.RootElement.GetProperty("lights").EnumerateArray())
                result.Add(new Light {Name=item.GetProperty("name").GetString()??"",Position=Position(item.GetProperty("position")),Color=Color(item.GetProperty("color")),Energy=item.GetProperty("energy").GetSingle()});
        }
        var path=Path.Combine(directory,world+"_channels.json");
        if(!File.Exists(path))return result;
        using(var doc=JsonDocument.Parse(File.ReadAllText(path)))
        {
            if(!doc.RootElement.TryGetProperty("lights",out var rows))return result;
            foreach(var row in rows.EnumerateArray())
            {
                var name=row.GetProperty("name").GetString();var light=result.Find(x=>x.Name==name);if(light==null)continue;
                foreach(var item in row.GetProperty("samples").EnumerateArray())
                    light.Samples.Add(new LightSample {Frame=item.GetProperty("frame").GetSingle(),Energy=item.GetProperty("energy").GetSingle(),Position=item.TryGetProperty("position",out var p)?Position(p):light.Position,Color=item.TryGetProperty("color",out var c)?Color(c):light.Color});
            }
        }
        return result;
    }
    private static Vector3 Position(JsonElement a)=>new(a[0].GetSingle(),a[2].GetSingle(),-a[1].GetSingle());
    private static Vector4 Color(JsonElement a)=>new(a[0].GetSingle(),a[1].GetSingle(),a[2].GetSingle(),1);
    private sealed class Light {public string Name="";public Vector3 Position;public Vector4 Color;public float Energy;public readonly List<LightSample> Samples=new();}
    private struct LightSample {public float Frame,Energy;public Vector3 Position;public Vector4 Color;}
}
